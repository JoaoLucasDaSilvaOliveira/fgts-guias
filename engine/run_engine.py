from fgts_guias.__main__ import main, configure_stdio
if __name__ == '__main__':
    configure_stdio()
    import sys
    if sys.argv[1:] == ['--check-chrome']:
        # Exercise the frozen executable and the actual installed launcher,
        # without navigating, logging in or touching an operator's profile.
        import asyncio
        import subprocess
        from fgts_guias.browser import chrome_path
        from fgts_guias.external import launch_external
        from playwright.async_api import async_playwright
        executable = chrome_path()
        if not executable:
            raise SystemExit('Google Chrome não encontrado')
        # Chrome's Windows GUI launcher does not implement --version. Verify
        # an installed system command there instead of opening a browser in CI.
        command = ['cmd.exe', '/c', 'ver'] if sys.platform == 'win32' else [executable, '--version']
        process = launch_external(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=30)
        if process.returncode:
            raise SystemExit(stderr.decode(errors='replace'))
        async def check_driver():
            async with async_playwright():
                pass
        asyncio.run(check_driver())
        print('Chrome localizado; comando externo e driver disponíveis:', stdout.decode(errors='replace').strip())
    else:
        main()
