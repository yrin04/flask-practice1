import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


class TodoApiTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 임시 폴더에 app.py를 복사해 테스트 전용 DB를 사용한다.
        cls.temp_dir = tempfile.TemporaryDirectory()
        source = Path(__file__).resolve().parent / 'app.py'
        copied_app = Path(cls.temp_dir.name) / 'app.py'
        shutil.copy2(source, copied_app)

        spec = importlib.util.spec_from_file_location('test_todo_app', copied_app)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

        cls.app = cls.module.app
        cls.db = cls.module.db
        cls.app.config['TESTING'] = True

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            cls.db.session.remove()
            cls.db.engine.dispose()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.client = self.app.test_client()

        # 각 테스트를 빈 데이터베이스에서 시작한다.
        with self.app.app_context():
            self.db.drop_all()
            self.db.create_all()

    def create_todo(self, text='우유 사기', note='2리터짜리로'):
        return self.client.post(
            '/api/todos/',
            json={'text': text, 'note': note}
        )

    def test_create_todo_with_note(self):
        response = self.create_todo()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['text'], '우유 사기')
        self.assertEqual(response.json['note'], '2리터짜리로')
        self.assertFalse(response.json['done'])

    def test_create_todo_without_note(self):
        response = self.client.post(
            '/api/todos/',
            json={'text': '책 반납'}
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['note'], '')

    def test_get_one_todo(self):
        created = self.create_todo()
        todo_id = created.json['id']

        response = self.client.get(f'/api/todos/{todo_id}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['text'], '우유 사기')
        self.assertEqual(response.json['note'], '2리터짜리로')

    def test_patch_todo(self):
        created = self.create_todo()
        todo_id = created.json['id']

        response = self.client.patch(
            f'/api/todos/{todo_id}',
            json={'done': True}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['done'])
        self.assertEqual(response.json['text'], '우유 사기')
        self.assertEqual(response.json['note'], '2리터짜리로')

    def test_filter_todos(self):
        first = self.create_todo()
        self.create_todo(text='책 반납', note='')

        self.client.patch(
            f"/api/todos/{first.json['id']}",
            json={'done': True}
        )

        all_todos = self.client.get('/api/todos/')
        done_todos = self.client.get('/api/todos/?done=true')
        undone_todos = self.client.get('/api/todos/?done=false')

        self.assertEqual(len(all_todos.json), 2)
        self.assertEqual(len(done_todos.json), 1)
        self.assertEqual(len(undone_todos.json), 1)
        self.assertEqual(done_todos.json[0]['text'], '우유 사기')
        self.assertEqual(undone_todos.json[0]['text'], '책 반납')

    def test_delete_todo(self):
        created = self.create_todo()
        todo_id = created.json['id']

        response = self.client.delete(f'/api/todos/{todo_id}')

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b'')
        self.assertEqual(
            self.client.get(f'/api/todos/{todo_id}').status_code,
            404
        )

    def test_not_found(self):
        response = self.client.get('/api/todos/999')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['message'], '999 번 할 일이 없습니다')


if __name__ == '__main__':
    unittest.main()