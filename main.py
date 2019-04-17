import os
from flask import Flask, Response, jsonify, abort, send_file, request
from flask_mysqldb import MySQL
import json
from flask_cors import CORS, cross_origin
import hashlib

app = Flask(__name__)
CORS(app)
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'compra'
mysql = MySQL(app)

#cargar todos los productos
@app.route("/productos/todos/<pagina>",methods=['GET'])
def todos(pagina):
    pagina = int(pagina)*10
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `productos` limit "+ str(pagina) +",10")
    row_headers=[x[0] for x in cur.description]
    rv = cur.fetchall()
    json_data=[]
    for result in rv:
        json_data.append(dict(zip(row_headers,result)))
    respuesta = {
        "error": False, 
        "productos": json_data
    }
    return jsonify(respuesta)

#buscar producto
@app.route("/productos/buscar/<producto>",methods=['GET'])
def buscar(producto):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `productos`WHERE producto LIKE  '%"+ producto +"%'")
    row_headers=[x[0] for x in cur.description] #this will extract row headers
    rv = cur.fetchall()
    json_data=[]
    for result in rv:
        json_data.append(dict(zip(row_headers,result)))
    respuesta = {
        "error": False, 
        "termino": producto,
        "productos": json_data
    }
    return jsonify(respuesta)

#cargar todas las categorias 
@app.route("/lineas",methods=['GET'])
def lineas():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `lineas`")
    row_headers=[x[0] for x in cur.description]
    rv = cur.fetchall()
    json_data=[]
    for result in rv:
        json_data.append(dict(zip(row_headers,result)))
    respuesta = {
        "error": False, 
        "lineas": json_data
    }
    return jsonify(respuesta)

#cargar categoria por el tipo
@app.route("/productos/porTipo/<id>",methods=['GET'])
def porTipo(id, pagina=0):
    if id=='0':
        respuesta ={
            "error" : True,
            "mensaje" : 'Falta el parametro del tipo'
        }
        return abort(400)
    cur = mysql.connection.cursor()
    pagina = pagina*10
    cur.execute("SELECT * FROM `productos` WHERE linea_id = "+ str(id) +" limit "+ str(pagina) +",10")
    row_headers=[x[0] for x in cur.description]
    rv = cur.fetchall()
    json_data=[]
    for result in rv:
        json_data.append(dict(zip(row_headers,result)))
    respuesta = {
        "error": False, 
        "productos": json_data
    }
    return jsonify(respuesta)

#cargar imagenes
@app.route("/productos/<img>",methods=['GET'])
def imagen(img):
    imagen_dir = os.path.join('./productos/', img+'.jpg')
    return send_file(imagen_dir)

#login
@app.route("/login",methods=['POST'])
def index():
    data = request.get_json()
    if data['correo'] == "" or data['contrasena'] == "":
        return  abort(400)
    #tenemos correo y contraseña en un post
    correo = data['correo']
    contrasena = data['contrasena']

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM login where correo = '"+ correo +"' and contrasena = '"+ contrasena +"'")
    rv = cur.fetchall()
    if len(rv)==0:
        respuesta = {
            "error": True, 
            "mensaje": "Usuario y/o contrasena no son validos"
        }
        return jsonify(respuesta)
    #tenemos usuario y contraseña validos
    iduser = list(rv[0])[0]

    #TOKEN
    token = hashlib.md5(correo.encode())
    token = token.hexdigest()

    cur = mysql.connection.cursor()
    cur.execute("UPDATE login SET token = '"+ str(token) +"' where id = "+ str(iduser) +"")
    mysql.connection.commit()
    respuesta = {
            "error" : False,
            "token" : str(token),
            "id_usuario" : iduser
    }
    return jsonify(respuesta)

#realizar orden de productos
@app.route("/pedidos/realizarOrden/<token>/<id_usuario>",methods=['POST'])
def realizarOrden(token = "0", id_usuario = "0"):
    data = request.get_json()
    if token == "0" or id_usuario == "0":
        return  abort(400)
    if data['items'] == "" or data['items'] == 0:
        return  abort(400)
    #items, usuario y token
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM login where id = '"+ id_usuario +"' and token = '"+ token +"'")
    rv = cur.fetchall()
    if len(rv)==0:
        respuesta = {
            "error": True, 
            "mensaje": "Usuario y token incorrectos"
        }
        return jsonify(respuesta)
    #usuario y token son correctos
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO ordenes (`usuario_id`) VALUES ('"+ str(id_usuario) +"')")
    cur.execute("SELECT last_insert_id()")
    mysql.connection.commit()
    ordenId = cur.fetchall()
    ordenId = list(ordenId[0])[0]

    for items in data['items']:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO ordenes_detalle (`producto_id`,`orden_id`) VALUES ('"+ str(items) +"','"+ str(ordenId) +"')")
        mysql.connection.commit()

    respuesta = {
        "error": False, 
        "mensaje": ordenId
    }
    return jsonify(respuesta)

#obtener pedidos
@app.route("/pedidos/obtenerPedidos/<token>/<id_usuario>",methods=['GET'])
def obtenerPedidos(token = "0", id_usuario = "0"):
    if token == "0" or id_usuario == "0":
        return  abort(400)
    #idusuario y token
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM login where id = '"+ id_usuario +"' and token = '"+ token +"'")
    rv = cur.fetchall()
    if len(rv)==0:
        respuesta = {
            "error": True, 
            "mensaje": "Usuario y token incorrectos"
        }
        return jsonify(respuesta)
    #usuario y token son correctos
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `ordenes` WHERE usuario_id = '"+ id_usuario +"'")
    rv = list(cur.fetchall())
    ordenes=[]
    creadoEn=[]
    for x in range(len(rv)):
        ordenes.append(rv[x][0])
        creadoEn.append(rv[x][2])
    respuestaF=[]
    pos=0
    for orden in ordenes:
        cur = mysql.connection.cursor()
        cur.execute("SELECT a.orden_id, b.* FROM ordenes_detalle a INNER JOIN productos b ON a.producto_id = b.codigo WHERE orden_id = '"+ str(orden) +"'")
        row_headers=[x[0] for x in cur.description]
        rv = cur.fetchall()
        json_data=[]
        for result in rv:
            json_data.append(dict(zip(row_headers,result)))
        respuesta = {
            "id" : ordenes[pos],
            "creado_en" : str(creadoEn[pos]),
            "detalle" : json_data
        } 
        pos+=1   
        respuestaF.append(respuesta)
    respuesta = {
            "error" : False,
            "ordenes" : respuestaF
        }
    return jsonify(respuesta) 

#borrar pedido
@app.route("/pedidos/borrarPedido/<token>/<id_usuario>/<ordenId>",methods=['GET'])
def borrarPedido(token = "0", id_usuario = "0", ordenId = "0"):
    if token == "0" or id_usuario == "0" or ordenId == "0":
        return  abort(400)
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM login where id = '"+ id_usuario +"' and token = '"+ token +"'")
    rv = cur.fetchall()
    if len(rv)==0:
        respuesta = {
            "error": True, 
            "mensaje": "Usuario y token incorrectos"
        }
        return jsonify(respuesta)
    #usuario y token son correctos
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM ordenes where id = '"+ ordenId +"' and usuario_id = '"+ id_usuario +"'")
    rv = cur.fetchall()
    if len(rv)==0:
        respuesta = {
            "error": True, 
            "mensaje": "Esa orden no puede ser borrada"
        }
        return jsonify(respuesta)
    #El usuario si puede eliminar la orden seleccionada
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM ordenes where id = '"+ ordenId +"'")
    #se borra la orden
    cur.execute("DELETE FROM ordenes_detalle where orden_id = '"+ ordenId +"'")
    mysql.connection.commit()
    respuesta = {
        "error": False, 
        "mensaje": "Orden eliminada"
    }
    return jsonify(respuesta)

if __name__ == '__main__':
    app.run(debug=True)

