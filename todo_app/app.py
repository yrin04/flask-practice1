from flask import Flask, Blueprint, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api, Resource, fields

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 없는 번호를 조회할 때 불필요한 안내 문구를 붙이지 않음
app.config['ERROR_404_HELP'] = False

# API 응답에서 한글이 그대로 보이도록 설정
app.config['RESTX_JSON'] = {'ensure_ascii': False}

db = SQLAlchemy(app)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(100), nullable=False)
    done = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Todo {self.id} {self.text}>'


# 기존 화면 라우트
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        db.session.add(Todo(text=request.form['todo']))
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


@app.route('/edit/<int:id>', methods=['POST'])
def edit(id):
    todo = db.get_or_404(Todo, id)
    todo.text = request.form['todo']
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/delete/<int:id>')
def delete(id):
    todo = db.get_or_404(Todo, id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for('index'))


# 실습 ②: /api 아래에 API와 문서 화면 구성
api_bp = Blueprint('api', __name__, url_prefix='/api')

api = Api(
    api_bp,
    version='1.0',
    title='Todo API',
    description='4장에서 만든 todo 앱의 API',
    doc='/docs'
)

ns = api.namespace('todos', description='할 일 하나하나를 다루는 곳')


# 실습 ③: 서버가 응답할 데이터 모양
todo_model = api.model('Todo', {
    'id': fields.Integer(
        readonly=True,
        description='줄 번호. 서버가 붙입니다'
    ),
    'text': fields.String(
        required=True,
        description='할 일 글자',
        example='우유 사기'
    ),
    'done': fields.Boolean(
        description='완료 여부',
        example=False
    )
})

# 생성하거나 수정할 때 받을 데이터 모양
todo_input = api.model('TodoInput', {
    'text': fields.String(
        required=True,
        description='할 일 글자',
        example='우유 사기'
    ),
    'done': fields.Boolean(
        description='완료 여부',
        example=False
    )
})


# 실습 ④: 목록 조회와 새 할 일 생성
@ns.route('/')
class TodoList(Resource):
    @ns.doc('목록 보기')
    @ns.marshal_list_with(todo_model)
    def get(self):
        """할 일을 전부 돌려준다"""
        return Todo.query.all()

    @ns.doc('새로 만들기')
    @ns.expect(todo_input, validate=True)
    @ns.marshal_with(todo_model, code=201)
    def post(self):
        """새 할 일을 하나 만든다"""
        todo = Todo(
            text=api.payload['text'],
            done=api.payload.get('done', False)
        )
        db.session.add(todo)
        db.session.commit()

        return todo, 201, {
            'Location': f'/api/todos/{todo.id}'
        }


app.register_blueprint(api_bp)

with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)