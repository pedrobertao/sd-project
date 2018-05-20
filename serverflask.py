import ldap
import hashlib
import mysql.connector
import datetime
import time
from flask import Flask, request, session, render_template, redirect, g, url_for
from base64 import b64decode, b16encode
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback

app = Flask(__name__)
app.secret_key = 'trabalho_de_sd_2018'

#LDAP
global con, ldap_base
ldap_base = "dc=sd,dc=com"
con = ldap.initialize('ldap://127.0.0.1')
my_password = 'admin'
con.simple_bind_s("cn=admin,dc=sd,dc=com", my_password)
# result = con.search_s(ldap_base, ldap.SCOPE_SUBTREE, query,['cn','mail','userPassword'])

#PubNub
global pubnub
pnconfig = PNConfiguration()
pnconfig.subscribe_key = 'sub-c-163d074e-4fa0-11e8-9b12-d6295e8dfe4d'
pnconfig.publish_key = 'pub-c-43a45a3e-507d-4731-aa9c-6fd3adb207fb'
pnconfig.ssl = False
pubnub = PubNub(pnconfig)

#DB Stuff
global db
db = mysql.connector.connect(user='root', password='root',
                              host='127.0.0.1',
                              database='trabalho')
database_status = "connected" if db.is_connected else "disconnected"
print("The database is " + database_status);
global cursor;
cursor = db.cursor()


# print(documents)
class MyListener(SubscribeCallback):
    def status(self, pubnub, status):
       pass
 
    def message(self, pubnub, message):
        print("Messangem sim",message.message)
        pass
 
    def presence(self, pubnub, presence):
        pass
 

pubnub.add_listener(MyListener())



def handle_publish_to_admin(userGroup,user):
    message = "O usuário %s acabou de assinar o documento" % user
    group = "adm_"+userGroup
    pubnub.publish().channel(group).message({'msg':message}).async(publish_callback)

def handle_insert_docs(groups,docType):
    global db
    cursor = db.cursor()
    querySearch = "select username from users where"
    for group in groups:
        querySearch+= " users.group ='"+group +"' or"

    cursor.execute(querySearch[:-3])
    users = [] 
    for row in cursor:
        users.append(row[0])

    docType = 'relatorio'
    queryValues = ""
    dateNow = int(time.time())
    for u in users:
        val = "( '%s', '%s',NULL, FROM_UNIXTIME(%s) ), " % (docType, u,dateNow)
        queryValues+= val
    finalQuery = "INSERT into userdocs (doc_type, username, signed , emitted) values " + queryValues
    print(finalQuery[:-2])
    cursor.execute(finalQuery[:-2])
    db.commit()

    return
    

def handle_publish_docs(groups):
    print("Groups to Publish")
    print(groups)
    global pubnub
    for group in groups:
        pubnub.publish().channel(group).message({'msg':'Você tem documento para assinar agora !'}).async(publish_callback)


def get_documents(user):
    query = ("SELECT userdocs.doc_type, userdocs.signed, documents.name, documents.fields"+
             " from userdocs, documents"+
             " where userdocs.username = '%s' and doc_type = '%s';")
    cursor.execute(query,(user))



def handle_login(user, password):
    global con,ldap_base
    query = "(uid=%s)" % user
    result = con.search_s(ldap_base, ldap.SCOPE_SUBTREE, query,['cn','mail','userPassword'])
    print(query,result)
    if result:
        #Esse é a hash a ser comparada vinda do LDAP
        result = result[0][1]['userPassword'][0].decode('utf-8').split('}')[1]
        #Algoritmo de comparação
        hashing = hashlib.md5()
        hashing.update(bytes(password, 'utf-8'))

        #Transformações finais
        user_password = b16encode(hashing.digest()).lower().decode('utf-8')
        ldap_password = b16encode(b64decode(result)).lower().decode('utf-8')
        print('user password sendo comparados', user_password, ldap_password)
        if user_password == ldap_password: return True
        else: return False

    else: return False

def publish_callback(result, status):
  print("resultado",result)
  print("resultado",status)
  pass

@app.before_request
def before_request():
    g.user = None
    print(request.path)
    if 'user' in session:
        g.userType = session['userType']
        g.user = session['user']
        g.userGroups = session['userGroups']
    else:
        if request.path != '/':
            return redirect(url_for('index'))




@app.route('/', methods=['GET', 'POST'])
def index():
    global db
    if request.method == 'GET':
        if 'user' in session:
            return redirect(url_for('profile'))
    if request.method == 'POST':
        user = request.form['username'] 
        password = request.form['password'] 
        if handle_login(user,password):
            cursor = db.cursor()
            query = ("SELECT users.type, users.group from users where username ='%s'" % (user))
            cursor = db.cursor()
            cursor.execute(query)
            for row in cursor:
                userType = row[0]
                groups = row[1].split(',')
                userGroups = row[1]

            session['user'] = user
            session['userType'] = userType
            session['userGroups'] = userGroups
            return redirect(url_for('index'))

    return render_template("login.html")

# @app.route("/profile/<name>")
@app.route("/documents",methods=['GET', 'POST'])
def documents(name=None):
    global db
    cursor = db.cursor()
    user = session['user']
    if request.method == 'GET':
        query = ("SELECT userdocs.id as id,documents.type, userdocs.signed, documents.name, documents.fields , documents.info "
                "from userdocs, documents "
                "where userdocs.username = %s and userdocs.doc_type = documents.type;")
        result =  cursor.execute(query,(user,))
        documents = []
        for row in cursor:
            # print(row)
            doc = {}
            doc['id'] = row[0]
            doc['type'] = row[1]
            doc['sign'] = row[2]
            doc['name'] = row[3]
            doc['fields'] = row[4]
            doc['info'] = row[5]
            documents.append(doc)
            
        # print(documents)

        return render_template("documents.html", documents=documents)
    else:
        docId = request.form['docId']
        docId = int(docId)

        dictInfo = request.form.to_dict()

        if 'verify' in dictInfo:
            return redirect(url_for('verify',docId = docId))
        else:
            return redirect(url_for('sign',docId = docId))

 

@app.route("/sign",methods=['GET', 'POST'])
def sign(doc_id=None):
    global db
    cursor = db.cursor()
    user = session['user']
    userGroup = session['userGroups']
    if request.method == 'GET':
        cursor = db.cursor()
        docId = request.args['docId'] 
        query = ("SELECT documents.fields as fields, documents.info as info "
                "from documents "
                "where documents.type in (select userdocs.doc_type from userdocs where userdocs.id = %d)") % int(docId)
        result = cursor.execute(query)
        
        docInfo = {}
        for row in cursor:
            docInfo['docId'] = docId
            fields = row[0].split(',')
            docInfo['fields'] = fields
            docInfo['info'] = row[1]
    
        return render_template("sign.html",docinfo=docInfo)

    else: 
        print("FORM FORM")
        docId = request.form['docId']
        cursor = db.cursor()
        dateNow = int(time.time())
        query= "UPDATE userdocs SET signed=FROM_UNIXTIME(%d) WHERE id=%d;" % (int(dateNow), int(docId))
        result =  cursor.execute(query)
        db.commit()
        handle_publish_to_admin(userGroup,user)
        return redirect(url_for('documents'))


@app.route("/verify")
def verify(verify=None):
    global db
    cursor = db.cursor()
    user = session['user']
    
    cursor = db.cursor()
    docId = request.args['docId'] 
    query = ("SELECT documents.fields as fields, documents.info as info, userdocs.signed as signed "
            "from documents, userdocs "
            "where documents.type in (select userdocs.doc_type from userdocs where userdocs.id = %d) and userdocs.id = %d") % (int(docId), int(docId))
    result = cursor.execute(query)
    docInfo = {}
    for row in cursor:
        docInfo['docId'] = docId
        fields = row[0].split(',')
        docInfo['fields'] = fields
        docInfo['info'] = row[1]
        docInfo['sign'] = row[2]

    return render_template("verify.html",docinfo=docInfo)


@app.route("/profile")
def profile(name=None):
    return render_template("profile.html")


@app.route("/publishdoc",methods=['GET', 'POST'])
def publishdoc():
    global pubnub,db
    if request.method == 'GET':
        user = session['user']
        query = ("SELECT documents.*, users.group "
                "FROM documents, users "
                "where users.username = '%s'") % user
        result = cursor.execute(query)
        documents = []
        for row in cursor:
            doc = {}
            doc['docId'] = row[0]
            doc['name'] = row[1]
            doc['type'] = row[2]
            fields = row[3].split(',')
            doc['fields'] = fields
            doc['info'] = row[4]
            groups = row[5].split(',')
            doc['groups'] = groups
            documents.append(doc)
        return render_template("publishdoc.html", documents = documents)
    else :
        groups = request.form.getlist('groups')
        docType = request.form['docType'] 
        handle_insert_docs(groups,docType)  
        handle_publish_docs(groups)
        return redirect(url_for('publishdoc'))

@app.route("/controldoc")
def controldoc():
    global pubnub,db
    user = session['user']
    groups = session['userGroups']
    groups = groups.split(',')
    querySearch =("SELECT *"
                  "FROM userdocs "
                  "where username in (select users.username from users where ")
    for group in groups:
        querySearch+= " users.group ='"+group +"' or"

    querySearch = querySearch[:-3] + ")"
    print(querySearch)
    result = cursor.execute(querySearch)
    documents = []
    for row in cursor:
        doc = {}
        doc['docId'] = row[0]
        doc['docType'] = row[1]
        doc['user'] = row[2]
        doc['signed'] = row[3]
        doc['emitted'] = row[4] 
        documents.append(doc)    
    return render_template("controldoc.html", documents = documents)


@app.route("/publish",methods=['GET', 'POST'])
def publish():
    global pubnub
    if request.method == 'POST':
        data = request.form.to_dict()
        print(data)
        return 'Foi'
    else :
        pubnub.publish().channel("adm_channel").message({'type': 'document_one', 'deadline': '12/12/2018'}).async(publish_callback)
        return "Publiquei !"

@app.errorhandler(404)
def page_not_found(e):
    # Todo handle not found
    return redirect(url_for('index'))
# @app.route('/')
# def hello():
#     return "Method used: %s" % request.method


# @app.route()
# @app.route('/test', methods=['GET', 'POST'])
# def test():
#     return 'HAHAHHAHAH'
    # if request.method == 'POST'
# @app.route('/documents/<username>')
# def documents(username):
#     return "Hello %s" % username

# @app.route('/post/<int:post_id>')
# def show_post(post_id):
#     return "Hello %s" % post_id

if __name__ == "__main__":
    app.run(host='localhost')

