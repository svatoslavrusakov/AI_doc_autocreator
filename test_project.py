import unittest
from pathlib import Path
from unittest.mock import patch
from models import Bank, Customer, Job
from pdf_generator import render_act_pdf
from main import LLMAgent, update_act_pdf, read_requisites


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.customer = Customer('Демо', '0'*10, '0'*13, 'Примерск', 'Пример П.П.', Bank('Учебный', '0'*9, '0'*20, '0'*20))

    def test_pdf(self):
        with patch('pdf_generator.OUTPUT_DIR', 'output'):
            a, total = render_act_pdf(self.customer, [Job('Строка'*1000, 1234)]*20, city='Примерск')
            b, _ = render_act_pdf(self.customer, [], city='Примерск')
            self.assertNotEqual(a, b)
            self.assertEqual(total, 24680)
            self.assertTrue(Path(a).read_bytes().startswith(b'%PDF'))
            with self.assertRaises(ValueError):
                render_act_pdf(self.customer, [Job('Работа', -1)], city='Примерск')
            with self.assertRaises(ValueError):
                render_act_pdf(self.customer, [], city='')

    def test_session_tool_state(self):
        from dataclasses import asdict
        from types import SimpleNamespace
        tools = []
        def graph(model, **kwargs):
            tools.append(kwargs['tools'][0])
            return SimpleNamespace(invoke=lambda *a, **k: {'messages': [SimpleNamespace(content='ok')]})
        with patch('main.create_react_agent', side_effect=graph), patch('main.render_act_pdf', return_value=('demo.pdf', 100)):
            first = LLMAgent(None, [update_act_pdf])
            second = LLMAgent(None, [update_act_pdf])
            for jobs in ([Job('A',100)], [Job('A',100), Job('B',200)], [Job('A',150), Job('B',200)], [Job('A',150)]):
                result = tools[0].invoke(dict(customer=asdict(self.customer), jobs=[asdict(j) for j in jobs], city='Примерск'))
                self.assertFalse(result.startswith('Ошибка'))
                self.assertEqual(first.current_act['jobs'], [asdict(j) for j in jobs])
            self.assertIsNone(second.current_act)
            saved = first.current_act.copy()
            with patch('main.render_act_pdf', side_effect=OSError):
                tools[0].invoke(dict(customer=asdict(self.customer), jobs=[], city='Примерск'))
            self.assertEqual(first.current_act, saved)
            self.assertEqual(first.invoke('продолжи'), 'ok')

    def test_requisites_explicit(self):
        self.assertIn('ДЕМОНСТРАЦИЯ', read_requisites('examples/requisites.txt'))


if __name__ == '__main__':
    unittest.main()
