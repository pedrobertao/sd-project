import ldap
import hashlib
import mysql.connector
from datetime import date
from datetime import datetime
import time
from flask import Flask, request, session, render_template, redirect, g, url_for, send_file
from base64 import b64decode, b16encode
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback
from src.util import create_document, encrypt_string

app = Flask(__name__)
app.secret_key = 'trabalho_de_sd_2018'
app.templates_auto_reload = True

#LDAP
global con, ldap_base
ldap_base = "dc=sd,dc=com"
con = ldap.initialize('ldap://127.0.0.1')
my_password = 'admin'
con.simple_bind_s("cn=admin,dc=sd,dc=com", my_password)

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


class MyListener(SubscribeCallback):
    def status(self, pubnub, status):
       pass

    def message(self, pubnub, message):
        pass

    def presence(self, pubnub, presence):
        pass


pubnub.add_listener(MyListener())




def handle_publish_to_admin(userGroup,user,docId):
    message = "O usuário %s acabou de assinar o documento de registro %d" % (user,int(docId))
    group = "adm_"+userGroup
    pubnub.publish().channel(group).message({'type':'normal', 'msg':message}).async(publish_callback)

def handle_mark_as_verified(docId):
    global db
    cursor = db.cursor()
    dateNow = int(time.time())
    query= "UPDATE userdocs SET verified=FROM_UNIXTIME(%d) WHERE id=%d;" % (dateNow, int(docId))
    cursor.execute(query)
    db.commit()
    return



def handle_insert_docs_users_only(users,docType,finalDate, verifyOnly):
    global db
    cursor = db.cursor()
    user = session['user']
    dateNow = int(time.time())
    queryValues = ""

    for u in users:
        val = "( '%s', '%s',NULL, FROM_UNIXTIME(%s), '%s', %s ), " % (docType, u,dateNow,finalDate,verifyOnly)
        queryValues+= val
    finalQuery = "INSERT into userdocs (doc_type, username, signed , emitted, finished, verifyOnly) values " + queryValues
    cursor.execute(finalQuery[:-2])
    db.commit()
    return


def handle_insert_docs(groups,docType,finalDate, verifyOnly):
    global db
    cursor = db.cursor()
    user = session['user']
    dateNow = int(time.time())

    querySearch = "select username from users where"
    for group in groups:
        querySearch+= " users.group ='"+group +"' or"


    cursor.execute(querySearch[:-3])
    users = []
    for row in cursor:
        users.append(row[0])

    queryValues = ""
    for u in users:
        val = "( '%s', '%s',NULL, FROM_UNIXTIME(%s), '%s', %s ), " % (docType, u,dateNow,finalDate,verifyOnly)
        queryValues+= val
    finalQuery = "INSERT into userdocs (doc_type, username, signed , emitted, finished, verifyOnly) values " + queryValues
    cursor.execute(finalQuery[:-2])
    db.commit()

    return


def handle_publish_docs(groups):
    global pubnub
    for group in groups:
        pubnub.publish().channel(group).message({'type':'normal', 'msg':'Você tem documento para assinar agora !'}).async(publish_callback)



def handle_login(user, password):
    global con,ldap_base
    query = "(uid=%s)" % user
    result = con.search_s(ldap_base, ldap.SCOPE_SUBTREE, query,['cn','mail','userPassword'])
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
  pass

@app.before_request
def before_request():
    g.user = None
    if 'user' in session:
        g.userType = session['userType']
        g.user = session['user']
        g.userGroups = session['userGroups']
    else:
        if request.path != '/' and '/static/' not in request.path:
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
        query = ("SELECT userdocs.id as id,documents.type, userdocs.signed, documents.name, documents.fields , documents.info, userdocs.finished, userdocs.verifyOnly ,userdocs.verified "
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
            finalDate = datetime.strptime(str(row[6]),"%Y-%m-%d %H:%M:%S")
            if finalDate.date() < date.today() and doc['sign'] == None:
                doc['finalDate'] = False
            else:
                doc['finalDate'] = row[6]
            doc['verifyOnly'] = row[7]
            doc['verified'] = row[8]
            documents.append(doc)

        # print(documents)

        return render_template("documents.html", documents=documents)
    else:
        docId = request.form['docId']
        docId = int(docId)

        dictInfo = request.form.to_dict()

        handle_mark_as_verified(docId)
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
    userType = session['userType']
    if request.method == 'GET':
        cursor = db.cursor()
        docId = request.args['docId']

        query = ("SELECT documents.fields as fields, documents.info as info, userdocs.verifyOnly "
                "from documents,userdocs "
                "where userdocs.id=%d and documents.type in (select userdocs.doc_type from userdocs where userdocs.id = %d)") % (int(docId),int(docId))
        result = cursor.execute(query)
        docInfo = {}
        for row in cursor:
            docInfo['docId'] = docId
            fields = row[0].split(',')
            docInfo['fields'] = fields
            docInfo['info'] = row[1]
            docInfo['verifyOnly'] = row[2]

        return render_template("sign.html",docinfo=docInfo)

    else:
        dictInfo = request.form.to_dict()
        docId = request.form['docId']
        cursor = db.cursor()
        dateNow = int(time.time())
        fields = ",".join(request.form.getlist('fields'))
        query= "UPDATE userdocs SET signed=FROM_UNIXTIME(%d),fieldsSign='%s' WHERE id=%d;" % (int(dateNow),fields,int(docId))
        result =  cursor.execute(query)
        db.commit()
        handle_publish_to_admin(userGroup,user,docId)
        return redirect(url_for('documents'))


@app.route("/verify")
def verify(verify=None):
    global db
    cursor = db.cursor()
    user = session['user']

    cursor = db.cursor()
    docId = request.args['docId']
    query = ("SELECT documents.fields as fields, documents.info as info, userdocs.signed as signed, userdocs.verifyOnly, userdocs.fieldsSign, documents.type "
            "from documents, userdocs "
            "where documents.type in (select userdocs.doc_type from userdocs where userdocs.id = %d) and userdocs.id = %d") % (int(docId), int(docId))
    result = cursor.execute(query)
    docInfo = {}
    for row in cursor:
        docInfo['docId'] = docId
        docInfo['info'] = row[1]
        docInfo['sign'] = row[2]
        docInfo['verifyOnly'] = row[3]
        fields = row[0].split(',')
        fieldsValues = row[4].split(',')
        for x in range(0,len(fields)):
            fields[x] = fields[x] + ':' + fieldsValues[x]
        docInfo['fields'] = fields
        docInfo['type'] = row[5]

    return render_template("verify.html",docinfo=docInfo)


@app.route("/signout")
def signout():
    session.pop('user')
    return redirect(url_for('index'))

@app.route("/profile", methods=['GET','POST'])
def profile(name=None):
    global db
    cursor = db.cursor()
    userGroups = session['userGroups'].split(',');
    user = session['user']
    userType = session['userType']

    if request.method == 'POST':
        message = ('[%s]: '% user)+request.form['message']
        groupsSelected = request.form.getlist('groups')
        for group in groupsSelected:
            pubnub.publish().channel(group).message({'type':'normal', 'msg':message}).async(publish_callback)
            if userType == 'user':
                pubnub.publish().channel('adm_'+group).message({'type':'normal', 'msg':message}).async(publish_callback)
        return redirect(url_for('profile'))

    else:
        userList = []
        queryUsers = ("SELECT users.username "
                    "FROM users "
                        "where ")
        if userType == 'adm':
            for group in userGroups:
                queryUsers+= " users.group ='"+group +"' or"
            queryUsers = queryUsers[:-3]
        else:
            queryUsers+= " users.group='%s' and users.username <> '%s'" %( userGroups[0] , user)
            admUser = 'adm_%s' % userGroups[0]
            userList.append(admUser)

        result = cursor.execute(queryUsers)
        for row in cursor:
            userList.append(row[0])

        print(queryUsers)
        return render_template("profile.html",userGroups=userGroups,userList=userList)




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

        queryUsers = ("SELECT users.username "
                            "FROM users "
                            "where ")
        for group in groups:
            queryUsers+= " users.group ='"+group +"' or"

        queryUsers = queryUsers[:-3]
        result = cursor.execute(queryUsers)
        userList = []
        for row in cursor:
            userList.append(row[0])

        for doc in documents:
            doc['userList'] = userList

        return render_template("publishdoc.html", documents = documents)
    else :
        dictInfo = request.form.to_dict()
        docType = request.form['docType']

        if 'verifyOnly' in dictInfo:
            verifyOnly = request.form['verifyOnly']
        else:
            verifyOnly = False

        finalDate = request.form['finalDate']
        if 'groups' in dictInfo:
            groups = request.form.getlist('groups')
            handle_insert_docs(groups,docType,finalDate,verifyOnly)
            handle_publish_docs(groups)
        else:
            users = request.form.getlist('users')
            handle_insert_docs_users_only(users,docType,finalDate,verifyOnly)
            handle_publish_docs(users)

        return redirect(url_for('publishdoc'))

@app.route("/controldoc", methods=['GET','POST'])
def controldoc():
    global pubnub,db
    user = session['user']
    groups = session['userGroups']
    groups = groups.split(',')

    if request.method == 'GET':
        querySearch =("SELECT *"
                    "FROM userdocs "
                    "where username in (select users.username from users where ")
        for group in groups:
            querySearch+= " users.group ='"+group +"' or"

        querySearch = querySearch[:-3] + ")"
        cursor = db.cursor()
        result = cursor.execute(querySearch)
        documents = []
        for row in cursor:
            doc = {}
            doc['docId'] = row[0]
            doc['docType'] = row[1]
            doc['user'] = row[2]
            doc['signed'] = row[3]
            doc['emitted'] = row[4]
            doc['finalDate'] = row[5]
            doc['admSign'] = row[7]
            doc['verified'] = row[8]
            documents.append(doc)
        return render_template("controldoc.html", documents = documents)
    else:
        docId = request.form['docId']
        dateNow = int(time.time())
        query= "UPDATE userdocs SET admSign=FROM_UNIXTIME(%d) WHERE id=%d;" % (dateNow, int(docId))
        cursor = db.cursor()
        result = cursor.execute(query)
        db.commit()
        return redirect(url_for('controldoc'))


@app.route("/publish",methods=['GET', 'POST'])
def publish():
    global pubnub
    if request.method == 'POST':
        data = request.form.to_dict()
    else :
        pubnub.publish().channel("adm_channel").message({'type': 'document_one', 'deadline': '12/12/2018'}).async(publish_callback)
        return "Publiquei !"



@app.route("/download")
def download(verify=None):
    global db
    cursor = db.cursor()
    user = session['user']

    cursor = db.cursor()
    docId = request.args['docId']
    query = "SELECT d.id, d.doc_type, d.username, d.emitted, d.fieldsSign from userdocs d WHERE d.id = '{}'".format(docId)
    result = cursor.execute(query)
    docInfo = {}
    for row in cursor:
        docInfo['docId'] = docId
        docInfo['docType'] = row[1]
        docInfo['user'] = row[2]
        docInfo['emitted'] = row[3]
        docInfo['signature'] = row[4]

    try:
        return send_file(create_document('./src/util/doc_template.docx',
                                            doc_type=docInfo['docType'],
                                            topic='TITULO',
                                            author=docInfo['user'],
                                            text='TEXTO',
                                            date=str(docInfo['emitted']),
                                            signature=encrypt_string(docInfo['signature'])),
                                        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                        attachment_filename= docId+'.docx')
    except Exception as e:
        return str(e)

@app.errorhandler(404)
def page_not_found(e):
    # Todo handle not found
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host='localhost')
