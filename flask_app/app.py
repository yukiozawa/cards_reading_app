from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from werkzeug import secure_filename
import os
import base64
import requests

app = Flask(__name__)
app.config.from_object('config')

def get_cards(user_id):
    connect =mysql.connector.connect(
            host='localhost',
            port=3306,
            user="root",
            passwd="",
            database='cards_app',
            charset="utf8")

    cursor = connect.cursor()
    sql = 'select * from cards where to_have_user_id="{}";'.format(user_id)
    print(sql)
    cursor.execute(sql)
    cards = cursor.fetchall()
    cursor.close()
    connect.close()
    return cards

    

@app.route('/')
def index():
    if not session.get('logged_in'):
        logged_in = False
        return render_template('login.html', message=logged_in)
    else:
        logged_in = True
        cards = get_cards(session['logged_in'])
        return redirect('cards')
    

# @app.route('/test')
# def test():
#     return 'Test Page'

# @app.route('/test2')
# def test2():
#     return render_template('test2.html', message='Hello!')

# @app.route('/admin_users')
# def admin_users():
#     connect =mysql.connector.connect(
#         host='localhost',
#         port=3306,
#         user="root",
#         passwd="",
#         database='cards_app3',
#         charset="utf8"
#     )
#     cursor = connect.cursor()
#     sql = 'SELECT * from admin_users;'
#     cursor.execute(sql)
#     admin_users = cursor.fetchall()
#     cursor.close()
#     connect.close()

#     return render_template('admin_users.html', admin_users = admin_users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        message = 'GET'
        return render_template('login.html', message = message)
    else:
        message = 'POST'
        entry_username = request.form['username']
        entry_pwd = request.form['pwd']

        connect =mysql.connector.connect(
        host='localhost',
        port=3306,
        user="root",
        passwd="",
        database='cards_app',
        charset="utf8")

        cursor = connect.cursor()
        sql = 'select * from admin_users where username="{}" and password="{}";'.format(entry_username, entry_pwd)
        print(sql)
        cursor.execute(sql)
        admin_user = cursor.fetchone()
        cursor.close()
        connect.close()
        
        print(admin_user)
        if admin_user == None:
            login_condition = "Failed"
            return render_template('login.html', message = message, entry_username=entry_username, entry_pwd=entry_pwd, login_condition=login_condition)
        else:
            session['logged_in'] = admin_user[0]
            login_condition = 'Success'
            cards = get_cards(session['logged_in'])
            return redirect('cards')

        

@app.route('/logout', methods=['GET'])
def logout():
    session.pop('logged_in', None)
    login_condition = 'Complete Logout!'
    return render_template('login.html', login_condition=login_condition)


@app.route('/cards', methods=['GET'])
def cards():
    if not session.get('logged_in'):
        print('Nothing Session')
        return redirect('login')
    else:
        print(session['logged_in'])

        cards = get_cards(session['logged_in'])

        return render_template('cards.html', cards=cards)

@app.route('/update', methods=['POST'])
def update():
    card_id = request.form['card_id']
    company_on_card = request.form['company_name']
    address_on_card = request.form['company_address']
    name = request.form['name']


    connect =mysql.connector.connect(
            host='localhost',
            port=3306,
            user="root",
            passwd="",
            database='cards_app',
            charset="utf8")

    cursor = connect.cursor()
    sql = 'UPDATE cards SET company_on_card="{}", address_on_card="{}", name_on_card = "{}" where card_id={};'.format(company_on_card, address_on_card, name, card_id)
    print(sql)
    cursor.execute(sql)
    connect.commit()
    cards = get_cards(session['logged_in'])
    return redirect('cards')

@app.route('/delete', methods=['POST'])
def delete():
    card_id = request.form['card_id']
    connect =mysql.connector.connect(
            host='localhost',
            port=3306,
            user="root",
            passwd="",
            database='cards_app3',
            charset="utf8")

    cursor = connect.cursor()
    sql = 'DELETE FROM cards_app3.cards where card_id={};'.format(card_id)
    print(sql)
    cursor.execute(sql)
    connect.commit()
    cards = get_cards(session['logged_in'])
    return redirect('cards')

@app.route('/new', methods=['POST'])
def new():
    # ファイルを読み込んでstatic/uploadsフォルダに保存
    img_file = request.files['img_file']
    filename = secure_filename(img_file.filename)
    filepath = os.path.join('static/uploads/', filename)
    img_file.save(filepath)
    
    # Vision APIでテキストを抽出
    with open(filepath, 'rb') as image:
        base64_image = base64.b64encode(image.read()).decode()
    
    url = 'https://vision.googleapis.com/v1/images:annotate?key={}'.format(app.config['API_KEY'])
    header = {'Content-Type': 'application/json'}
    body = {
        'requests': [{
            'image': {
                'content': base64_image,
            },
            'features': [{
                'type': 'TEXT_DETECTION',
                'maxResults': 1,
            }]

        }]
    }
    response = requests.post(url, headers=header, json=body).json()
    # print(response)
    text = response['responses'][0]['textAnnotations'][0]['description'] if len(response['responses'][0]) > 0 else ''    

    # Natural Language APIで抽出したtextに意味をつける
    url = 'https://language.googleapis.com/v1beta1/documents:analyzeEntities?key={}'.format(app.config['API_KEY'])
    header = {'Content-Type': 'application/json'}
    body = {
        "document": {
            "type": "PLAIN_TEXT",
            "language": "JA",
            "content": text
        },
        "encodingType": "UTF8"
    }
    
    entities = requests.post(url, headers=header, json=body).json()
    # print(response)
    required_entities = {'ORGANIZATION': '', 'PERSON': '', 'LOCATION': ''}
    for entity in entities['entities']:
        t = entity['type']
        if t in required_entities:
            required_entities[t] += entity['name']
    print(required_entities)

    # 紐付けた情報をそれぞれの変数に入れる
    company_on_card = required_entities['ORGANIZATION']
    address_on_card = required_entities['LOCATION']
    name_on_card = required_entities['PERSON']

    # それぞれの情報を新しいレコードとして挿入する
    connect =mysql.connector.connect(
            host='localhost',
            port=3306,
            user="root",
            passwd="",
            database='cards_app',
            charset="utf8")

    cursor = connect.cursor()
    sql = 'INSERT INTO cards(to_have_user_id, company_on_card, name_on_card, address_on_card) values({}, "{}", "{}", "{}");'.format(session['logged_in'], company_on_card, name_on_card, address_on_card)
    print(sql)
    cursor.execute(sql)
    connect.commit()

    return redirect('cards')


if __name__ == '__main__':
    app.run(port=8000, debug=True)