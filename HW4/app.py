from flask import Flask, render_template, request, redirect, url_for, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api, Resource, fields

app = Flask(__name__)

app.config['RESTX_ERROR_404_HELP'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'

db = SQLAlchemy(app)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(100), nullable=False)
    note = db.Column(db.String(200), default='')
    done = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Todo {self.id} {self.text}>'


# 기존 할 일 화면
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        todo = Todo(
            text=request.form['todo'],
            note=request.form['note']
        )
        db.session.add(todo)
        db.session.commit()
        return redirect(url_for('index'))

    todos = Todo.query.all()
    return render_template('index.html', todos=todos)


@app.route('/toggle/<int:id>')
def toggle(id):
    todo = db.get_or_404(Todo, id)
    todo.done = not todo.done
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    todo = db.get_or_404(Todo, id)

    if request.method == 'POST':
        todo.text = request.form['todo']
        todo.note = request.form['note']
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit.html', todo=todo)


@app.route('/delete/<int:id>')
def delete(id):
    todo = db.get_or_404(Todo, id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for('index'))


# API 설정
api_bp = Blueprint('api', __name__, url_prefix='/api')

api = Api(
    api_bp,
    version='1.0',
    title='Todo API',
    description='할 일 관리 API',
    doc='/docs'
)

ns = api.namespace('todos', description='할 일 관리')


# API가 응답할 데이터 형식
todo_model = api.model('Todo', {
    'id': fields.Integer(description='할 일 번호'),
    'text': fields.String(description='할 일', example='우유 사기'),
    'done': fields.Boolean(description='완료 여부', example=False),
    'note': fields.String(description='설명', example='2리터짜리로')
})


# API가 입력받을 데이터 형식
todo_input = api.model('TodoInput', {
    'text': fields.String(description='할 일', example='우유 사기'),
    'done': fields.Boolean(description='완료 여부', example=False),
    'note': fields.String(description='설명', example='2리터짜리로')
})


@ns.route('/')
class TodoList(Resource):

    @ns.doc('목록 보기')
    @ns.param('done', 'true면 완료한 할 일, false면 완료하지 않은 할 일')
    @ns.marshal_list_with(todo_model)
    def get(self):
        """할 일 목록을 조회한다."""
        todos = Todo.query
        done = request.args.get('done')

        if done is not None:
            todos = todos.filter_by(done=(done.lower() == 'true'))

        return todos.all()

    @ns.doc('할 일 만들기')
    @ns.expect(todo_input)
    @ns.marshal_with(todo_model, code=201)
    def post(self):
        """새로운 할 일을 등록한다."""
        data = api.payload or {}

        if not data.get('text'):
            ns.abort(400, '할 일을 입력해 주세요')

        todo = Todo(
            text=data['text'],
            done=data.get('done', False),
            note=data.get('note', '')
        )

        db.session.add(todo)
        db.session.commit()

        return todo, 201


@ns.route('/<int:id>')
@ns.param('id', '할 일 번호')
class TodoResource(Resource):

    def find_todo(self, id):
        todo = db.session.get(Todo, id)

        if todo is None:
            ns.abort(404, f'{id} 번 할 일이 없습니다')

        return todo

    @ns.doc('할 일 하나 보기')
    @ns.marshal_with(todo_model)
    def get(self, id):
        """할 일 하나를 조회한다."""
        return self.find_todo(id)

    @ns.doc('할 일 전체 수정하기')
    @ns.expect(todo_input)
    @ns.marshal_with(todo_model)
    def put(self, id):
        """할 일의 전체 내용을 수정한다."""
        todo = self.find_todo(id)
        data = api.payload or {}

        if not data.get('text'):
            ns.abort(400, '할 일을 입력해 주세요')

        todo.text = data['text']
        todo.done = data.get('done', False)
        todo.note = data.get('note', '')

        db.session.commit()

        return todo

    @ns.doc('할 일 일부 수정하기')
    @ns.expect(todo_input)
    @ns.marshal_with(todo_model)
    def patch(self, id):
        """입력한 항목만 수정한다."""
        todo = self.find_todo(id)
        data = api.payload or {}

        if 'text' in data:
            todo.text = data['text']

        if 'done' in data:
            todo.done = data['done']

        if 'note' in data:
            todo.note = data['note']

        db.session.commit()

        return todo

    @ns.doc('할 일 삭제하기')
    @ns.response(204, '삭제 완료')
    def delete(self, id):
        """할 일을 삭제한다."""
        todo = self.find_todo(id)

        db.session.delete(todo)
        db.session.commit()

        return '', 204


app.register_blueprint(api_bp)


with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)