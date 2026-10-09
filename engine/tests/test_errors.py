import unittest
from fgts_guias.errors import user_message
from fgts_guias.domain import period
from fgts_guias.browser import Attention

class MessageTests(unittest.TestCase):
    def test_technical_details_do_not_reach_operator(self):
        message = user_message(RuntimeError('Locator.wait_for failed: selector #secret\nCall log: protocol error'))
        self.assertNotIn('Locator', message)
        self.assertNotIn('#secret', message)
        self.assertIn('Retomar', message)

    def test_access_errors_explain_next_action(self):
        self.assertIn('permissão', user_message(PermissionError('/private/file')))
        self.assertIn('não foi encontrado', user_message(FileNotFoundError('/private/file')))
        self.assertNotIn('/private', user_message(FileNotFoundError('/private/file')))

    def test_app_validation_remains_specific(self):
        try:
            period('wrong')
        except ValueError as error:
            self.assertIn('mês e o ano', user_message(error))
        self.assertEqual(user_message(Attention('Confira o certificado.')), 'Confira o certificado.')

    def test_timeout_explains_recovery_without_reemission(self):
        self.assertIn('guia existente', user_message(TimeoutError('raw technical detail')))
