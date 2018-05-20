# TEST STUFF

# groups = ['ti']
# query = "select username from users where"
# for group in groups:
#     query+= " users.group ='"+group + "' or"

# query+= " false"
# print (query)
# print(query)
# query = ("select username from users where users.group = 'ti'")

# cursor.execute(query)
# users = [] 
# for row in cursor:
#     users.append(row[0])

# docType = 'relatorio'
# queryValues = ""
# dateNow = int(time.time())
# print("E AE?!")
# for u in users:
#     val = "( '%s', '%s',NULL, %s ) " % (docType, u,dateNow)
#     queryValues+= val

# print(queryValues)



# query = ("SELECT * from documents")
# result = cursor.execute(query)
# documents = []
# for row in cursor:
#     print(row)
#     doc = {}
#     doc['name'] = row[1]
#     doc['type'] = row[2]
#     fields = row[3].split(',')
#     doc['fields'] = fields
#     doc['info'] = row[4]
#     documents.append(doc)

# query = ("SELECT documents.fields as fields, documents.info as info "
#         "from documents "
#         "where documents.type in (select userdocs.doc_type from userdocs where userdocs.id = %d)" % (2))
# result = cursor.execute(query)
# print("MEU testes !")
# for row in cursor:
#     print('doc')
#     print(row)
# user = 'Pedro'
# query = ("SELECT documents.type, userdocs.signed, documents.name, documents.fields "
#          "from userdocs, documents "
#          "where userdocs.username = %s and userdocs.doc_type = documents.type;")
# cursor.execute(query,(user,)) esse krai espera uma tupla
# for row in cursor:
#     print(row)
# user = 'pedro'
# query = ("SELECT documents.type, userdocs.signed, documents.name, documents.fields "
#                 "from userdocs, documents "
#                 "where userdocs.username = %s and userdocs.doc_type = documents.type;")
# result = cursor.execute(query,(user,))

# documents = []
# for row in cursor:
#     print(row)
#     doc = {}
#     doc['type'] = row[0]
#     doc['sign'] = row[1]
#     doc['name'] = row[2]
#     doc['fields'] = row[3]
#     documents.append(doc)

# TEST STUF