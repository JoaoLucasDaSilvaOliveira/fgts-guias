"""Translate operational failures into instructions for the operator."""

def user_message(error):
    name = type(error).__name__
    if name == 'TimeoutError':
        return 'O portal demorou para responder. Abra o Chrome e confira a página. Depois, clique em Retomar. Se a emissão já foi solicitada, o app buscará a guia existente.'
    if name == 'TargetClosedError':
        return 'O Chrome foi fechado ou desconectado. Abra o Chrome pelo app e inicie o lote novamente para recuperar as guias já solicitadas.'
    if isinstance(error, PermissionError):
        return 'Sem permissão para acessar o arquivo ou a pasta. Escolha uma pasta onde possa salvar arquivos e tente novamente.'
    if isinstance(error, FileNotFoundError):
        return 'O arquivo ou a pasta não foi encontrado. Confira o local informado e tente novamente.'
    if isinstance(error, OSError):
        return 'Não foi possível acessar o arquivo ou a pasta. Confira se está disponível e se há espaço para salvar a guia.'
    # Messages raised by the app are written for the operator; third-party
    # exception text (selectors, traces, protocol and paths) stays diagnostic.
    if type(error).__module__.startswith('fgts_guias'):
        return str(error)
    traceback = error.__traceback__
    while traceback and traceback.tb_next:
        traceback = traceback.tb_next
    if isinstance(error, ValueError) and traceback and '/fgts_guias/' in traceback.tb_frame.f_code.co_filename.replace('\\', '/'):
        return str(error)
    return 'Não foi possível concluir esta etapa. Abra o Chrome, confira a página e clique em Retomar. Se a emissão já foi solicitada, o app buscará a guia existente.'
