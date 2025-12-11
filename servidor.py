import socket # Para usar sockets TCP
import sys # Para admitir argumentos 
import argparse as ap # Podemos importar módulos con nombre largo y darles un alias más corto
import os

#Información: los nombres de fichero se pueden usar como ruta para navegar entre ellos, es decir, si tenemos un fichero en la ruta raiz del programa solo debemos indicar su nombre:
# UPLOAD_FILE fichero.txt
#Pero si queremos hacerlo de un fichero que esté dentro de un directorio debería ser:
# UPLOAD_FILE "ruta/fichero.txt"
#--EXTRA--
#Si usas rutas de usuario deberías de controlar la ruta desde la carpeta del mismo y tener cuidado con las '/' que causan la mayoría de problemas.

def leer_fichero(nombre_fichero):
    
    try:
        fichero=open(nombre_fichero,'rb')
        return (True, fichero.read())
    except:
        return (False, b'')

#--EXTRA--
#Listar ficheros debería contener la ruta del directorio del usuario como argumento para usarse en listdir y que liste la ruta que indicas

def listar_ficheros(ruta="."):
    #Listar ficheros, función listdir()
    try:
        elementos = os.listdir(ruta)
        # Filtrar solo los que sean archivos
        archivos = [e for e in elementos if os.path.isfile(os.path.join(ruta, e))]
        return "\n".join(archivos) if archivos else "No hay archivos en la ruta."
    except FileNotFoundError:
        return f"Error: La ruta '{ruta}' no existe."
    except NotADirectoryError:
        return f"Error: '{ruta}' no es un directorio."
    except PermissionError:
        return f"Error: No tienes permisos para acceder a '{ruta}'."

def borrar_fichero(nombre_fichero):
    try:
        #Borrar fichero, función remove()
        os.remove(nombre_fichero)
        return "DELETED"
    except FileNotFoundError:
        return "ERROR"
    except PermissionError:
        return "ERROR"
    except Exception:
        return "ERROR"
    


def descargar_fichero(conn, fichero):
    try:
        # Comprobar que existe
        if not os.path.isfile(fichero):
            conn.sendall("ERROR".encode("ascii"))
            return

        # Leer archivo
        with open(fichero, "rb") as f:
            contenido = f.read()

        # Mandar tamaño del fichero (cadena)
        tam = str(len(contenido))
        conn.sendall(tam.encode("ascii"))

        # Esperar ACK del cliente
        ack = conn.recv(1024).decode("ascii")
        if ack != "ACK":
            conn.sendall("ERROR".encode("ascii"))
            return

        # Enviar contenido del fichero
        conn.sendall(contenido)

    except PermissionError:
        conn.sendall(f"ERROR".encode("ascii"))
    except Exception as e:
        conn.sendall(f"ERROR".encode("ascii"))

def subir_fichero(conn,fichero):
    try:
        #Enviar primer ACK
        conn.sendall("UPLOAD_ACK".encode("ascii"))
        #Recibir tamaño del fichero
        tam_str = conn.recv(1024).decode("ascii")
        try:
            tam = int(tam_str)
        except ValueError:
            err = "Error: tamaño de fichero inválido."
            conn.sendall(err.encode("ascii"))
            return err

        #Confirmar tamaño recibido
        conn.sendall("UPLOAD_ACK".encode("ascii"))

        #Recibir datos hasta completar longitud
        recibido = 0
        nombre = os.path.basename(fichero)
        # Si ya existe, renombrar como <nombre-copia>
        if os.path.exists(nombre):
            base, ext = os.path.splitext(nombre)
            candidato = f"{base}-copia{ext}"
            contador = 1
            while os.path.exists(candidato):
                candidato = f"{base}-copia{contador}{ext}"
                contador += 1
            nombre = candidato
        with open(nombre, "wb") as f:
            while recibido < tam:
                bloque = conn.recv(min(4096, tam - recibido))
                if not bloque:
                    err = "Error: conexión cerrada antes de recibir el fichero completo."
                    conn.sendall(err.encode("ascii"))
                    return err
                f.write(bloque)
                recibido += len(bloque)

        #Confirmar recepción de datos
        conn.sendall("DATA_RECEIVED\n".encode("ascii"))

        #Mensaje final de éxito
        response = f"SUCCESS: Fichero '{nombre}' subido correctamente.\n"
        conn.sendall(response.encode("ascii"))
        return response

    except PermissionError:
        msg = f"Error: permisos insuficientes para escribir '{fichero}'."
        conn.sendall(msg.encode("ascii"))
        return msg
    except Exception as e:
        msg = f"Error al subir fichero: {e}"
        conn.sendall(msg.encode("ascii"))
        return msg


def mover_fichero(fichero, destino):
    try:
        #Abrir fichero y leer todo el contenido
        with open(fichero, "rb") as f:
            contenido = f.read()

        #Crear un fichero en el directorio destino indicado y escribir el contenido obtenido
        os.makedirs(destino, exist_ok=True)
        nombre = os.path.basename(fichero)
        ruta_destino = os.path.join(destino, nombre)
        with open(ruta_destino, "wb") as f:
            f.write(contenido)

        #Borrar fichero de la ruta actual
        os.remove(fichero)
        #Enviar mensaje SUCCESS
        response = f"SUCCESS: Fichero '{nombre}' movido a '{destino}'."
        return response
    except FileNotFoundError:
        return f"Error: El fichero '{fichero}' no existe."
    except PermissionError:
        return f"Error: Permisos insuficientes para mover '{fichero}'."
    except Exception as e:
        return f"Error al mover fichero: {e}"

def crear_directorio(nombre_direccion):
    
    # Comprobar si ya existe
    if os.path.exists(nombre_direccion):
        response = f"Error: La ruta '{nombre_direccion}' ya existe."
        return response

    try:
        # Crear el directorio
        os.mkdir(nombre_direccion)
        # Enviar mensaje SUCCESS
        response = f"SUCCESS: Directorio '{nombre_direccion}' creado correctamente."
    except PermissionError:
        response = f"Error: No tienes permisos para crear '{nombre_direccion}'."
    except Exception as e:
        response = f"Error al crear el directorio: {e}"

    return response

def borrar_directorio(nombre_direccion):
    # Comprobar si existe
    if not os.path.exists(nombre_direccion):
        response = "Error: El directorio '{nombre_direccion}' no existe."
        return response

    # Comprobar si es realmente un directorio
    if not os.path.isdir(nombre_direccion):
        response = f"Error: '{nombre_direccion}' no es un directorio."
        return response

    # Comprobar si está vacío
    if os.listdir(nombre_direccion):
        response = f"Error: El directorio '{nombre_direccion}' no está vacío y no se puede eliminar."
        return response

    try:
        # Eliminar el directorio
        os.rmdir(nombre_direccion)
        # Enviar mensaje SUCCESS
        response = f"SUCCESS: Directorio '{nombre_direccion}' eliminado correctamente."
    except PermissionError:
        response = f"Error: No tienes permisos para eliminar '{nombre_direccion}'."
    except Exception as e:
        response = f"Error al eliminar el directorio: {e}"

    return response

def listar_directorio(nombre_direccion):
    #Comprobar si existe
    if not os.path.exists(nombre_direccion):
        response = f"Error: La ruta '{nombre_direccion}' no existe."
        return response
    if not os.path.isdir(nombre_direccion):
        response = f"Error: '{nombre_direccion}' no es un directorio."
        return response
    #Leer todo el contenido de la misma
    try:
        contenido = os.listdir(nombre_direccion)
        directorios = [d for d in contenido if os.path.isdir(os.path.join(nombre_direccion, d))]
        if directorios:
            response = "Directorios en " + nombre_direccion + ":\n" + "\n".join(directorios)
        else:
            response = f"No hay subdirectorios en '{nombre_direccion}'."
    except PermissionError:
        response = f"Error: No tienes permisos para acceder a '{nombre_direccion}'."
    #Enviar contenido
    return response

def help():
    #Se debe enviar información de los comandos.
    comandos = """
Comandos disponibles:

1. SHUTDOWN
   - Apaga el servidor.
   - Uso: SHUTDOWN

2. LIST_FILES [ruta]
   - Lista solo los ficheros en la ruta indicada (por defecto la actual).
   - Uso: LIST_FILES [ruta]

3. DOWNLOAD_FILE <fichero>
   - Descarga un fichero desde el servidor al cliente.
   - Uso: DOWNLOAD_FILE <nombre_fichero>

4. DELETE_FILE <fichero>
   - Borra un fichero en el servidor.
   - Uso: DELETE_FILE <nombre_fichero>

5. UPLOAD_FILE <fichero>
   - Sube un fichero desde el cliente al servidor.
   - Uso: UPLOAD_FILE <nombre_fichero>

6. MOVE_FILE <fichero> <destino>
   - Mueve un fichero a un directorio destino.
   - Uso: MOVE_FILE <nombre_fichero> <ruta_destino>

7. CREATE_DIR <nombre>
   - Crea un nuevo directorio en el servidor.
   - Uso: CREATE_DIR <nombre_directorio>

8. DELETE_DIR <nombre>
   - Borra un directorio en el servidor.
   - Uso: DELETE_DIR <nombre_directorio>

9. LIST_DIR [ruta]
   - Lista los subdirectorios en la ruta indicada (por defecto la actual).
   - Uso: LIST_DIR [ruta]

10. RENAME_FILE <fichero> <nuevo_nombre>
    - Renombra un fichero existente.
    - Uso: RENAME_FILE <nombre_actual> <nuevo_nombre>

11. HELP
    - Muestra esta ayuda.
    - Uso: HELP
"""
    return comandos
def renombrar_fichero(fichero, nuevo_nombre):
    try:
        # Comprobar si el fichero existe
        if not os.path.isfile(fichero):
            return "RENAME_ERROR"

        # Renombrar el fichero
        os.rename(fichero, nuevo_nombre)
        return "RENAMED"
    except FileNotFoundError:
        return "RENAME_ERROR"
    except PermissionError:
        return "RENAME_ERROR"
    except Exception:
        return "RENAME_ERROR"

# --EXTRA--

def obtener_usuarios():
    try:
        with open("usuarios.txt", 'r') as fUsuarios:
            usuarios=fUsuarios.read().splitlines()

            lista_usuarios=[]
            for u in usuarios:
                if not u.strip():
                    continue
                
                credenciales= u.strip().split(",")

                usr=[("usuario",credenciales[0]), ("contrasenia", credenciales[1])]
                lista_usuarios.append(dict(usr))
    except Exception as e:
        return "ERROR"+e
    
    return lista_usuarios

# --EXTRA--

def iniciar_sesion(usuario, contrasenia):

    usuarios=obtener_usuarios()

    #Comprobar si el usuario está en la lista
    #Comprobar contraseña del usuario

    return #(inicio_sesion, ruta_usuario)
# --EXTRA--

def registrar_usuario(usuario, contrasenia, confirmacion):
    usuarios=obtener_usuarios()

    #Comprobar si ese nombre de usuario esta registrado
    #Si no está registrado, se comprueba que la contraseña y la confirmación son la misma.
    #Registrar usuario en fichero usuarios.txt
    #Crear directorio personal para el usuario
    #Devolver SUCCESS
    return response

# --EXTRA--

def compartir_fichero(fichero, usuario):

    #Comprobar que el fichero existe
    #Leer el contenido del fichero
    #Crear fichero con mismo nombre en el directorio del usuario destinatario
    #Escribir el contenido del fichero en el fichero del destinatario
    return response
    



if __name__ == '__main__':

    #--EXTRA--
    #Este bloque hace que se cree un fichero donde se registran los usuarios y sus contraseñas
    """
    if not os.path.exists('usuario.txt'):
        file=open('usuario.txt', 'wb')
        file.close()
    """

    # Definimos el parseador. Por convenio, los argumentos opcionales se encabezan con '--'
    parser = ap.ArgumentParser(prog=sys.argv[0], description='Un servidor no concurrente TCP de hola mundo')
    parser.add_argument('--ip', help='IP del servidor', default='0.0.0.0')
    parser.add_argument('--puerto', type=int, help='Puerto TCP de salida', default=5005, choices=range(1024,65535), metavar='1024-65535') 
    parser.add_argument('--tam_buf', type=int, help='Longitud del buffer interno', default=4096) # Buffer corto para que responda antes
    
    # Parseamos los argumentos de acuerdo al parser
    args = parser.parse_args(sys.argv[1:])  #parseamos lo que viene de la línea de comandos desde el 1

    #--EXTRA--

    #Información para actividad extra: Se debería controlar con una ruta de usuario para saber si se ha iniciado sesión, o no, y en que directorio personal guardar los mensajes.
    #Puedes usar esta variable

    #ruta_usuario=''

    #Al principio debería estar vacía para indicar al usuario que debe iniciar sesión antes de realizar cualquier otra acción

    #INICIALIZACIÓN DEL SOCKET
    # Inicializacmos el servidor: empezamos a esperar conexiones. Para más información consulte: https://wiki.python.org/moin/HowTo/Sockets
    # 1. Declaramos el socket -> función socket(family, type, protocolo(por defecto es TCP no es necesario especificar))
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # decimos que se pueda reusar el puerto sin esperar -> setsockopt(level, optname, value)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 2. Lo ligamos a una IP y puerto -> bind(ip, port)
    
    servidor.bind((args.ip, args.puerto))
    # 3. Podemos encolar hasta una solicitud -> listen(cantidad de conexiones en cola)
    servidor.listen(1)

    shutdown = False # Variable flag que controla si queremos finalizar el servidor. En el caso de que reciba 'shutdown' terminará su ejecución.

    print ("Servidor configurado, esperando conexiones por el puerto", args.puerto)

    
    
    while not shutdown:
        # 4. Aceptamos cliente accept()
        conn, addr = servidor.accept()
        print(f"Aceptado un cliente con (IP, puerto)-> {addr[0]}: {addr[1]}" )

        try:
            data=conn.recv(args.tam_buf) # Recibimos datos -> recv(tamaño del buffer)
            if not data: # Si no se reciben datos --> se ha desconectado
                break
            
            data_str=data.decode("ascii", errors="ignore") #Convertir de binario a string con data.decode(codificación, errores) en codificación ascii e ignorando errores de conversión

            data_list = data_str.split()#Convierte cada palabra de la cadena en un vector 

            print ('Got command:', data_str)

            orden = data_list[0].upper()     #La orden se corresponde con la primera palabra (convertimos en mayuscula)
            
            #AYUDA PARA REALIZAR LOS BLOQUES DE CÓDIGO DE COMANDOS
            #Aquí entramos en la elección para que el servidor ejecute la orden que se solicita, usar la función send(mensaje).
            #El mensaje previamente deberia estar codificado en ascii con la función encode(codificación).
            #Previamente al envío de datos, se debe comprobar los errores, de haber alguno, la información que tiene que enviar el servidor es de un error para que el cliente interprete la información.

            #--EXTRA--
            #Deberiamos encapsular esto dentro de otro bloque donde se compruebe si el usuario ha iniciado sesión con la variable que se dió anteriormente.
            if orden == 'SHUTDOWN':

                #Cambiar el estado del server a shutdown
                shutdown = True
                conn.sendall(b"Servidor apagandose...\n")
                print("Servidor apagándose por orden del cliente.")
                conn.close()
                break
                
            elif (orden == 'LIST_FILES'):
                # Comprobar si se pasó ruta
                ruta = data_list[1] if len(data_list) > 1 else "."
                response = listar_ficheros(ruta)
                conn.sendall(response.encode())    
                

            elif orden == 'DOWNLOAD_FILE':
                    
                if len(data_list) > 1:
                    fichero = data_list[1]
                    descargar_fichero(conn, fichero)
                else:
                    response = "Error: Debes especificar el fichero a descargar."
                    conn.sendall(response.encode("ascii"))

            elif orden == 'DELETE_FILE':
                    
                if len(data_list) > 1:
                    fichero = data_list[1]   # nombre o ruta del fichero a borrar
                    response = borrar_fichero(fichero)
                    conn.sendall(response.encode("ascii"))
                else:
                    response = "ERROR"
                    conn.sendall(response.encode("ascii"))

            elif orden == 'UPLOAD_FILE':   
                if len(data_list) > 1:
                    fichero = data_list[1]
                    subir_fichero(conn,fichero)
                else:
                    response = "Error: Debes especificar un nombre de fichero."
                    conn.sendall(response.encode("ascii"))

            elif orden == 'MOVE_FILE':  
                    
                if len(data_list) > 2:
                    fichero = data_list[1]   
                    destino = data_list[2]  
                    response = mover_fichero(fichero, destino)
                    conn.sendall(response.encode("ascii"))
                else:
                    response = "Error: Debes especificar fichero y destino."
                    conn.sendall(response.encode("ascii"))

            elif orden == 'CREATE_DIR':

                if len(data_list) > 1:
                    nombre = data_list[1]
                    response = crear_directorio(nombre)
                else:
                    response = "Error: Debes especificar un nombre de directorio."
                conn.sendall(response.encode("ascii"))

            elif orden == 'DELETE_DIR':
                
                if len(data_list) > 1:
                    nombre = data_list[1]
                    response = borrar_directorio(nombre)
                else:
                    response = "ERROR: Debes especificar un nombre de directorio."
                conn.sendall(response.encode("ascii"))

            elif orden == 'LIST_DIR':

                ruta = data_list[1] if len(data_list) > 1 else "."
                response = listar_directorio(ruta)
                conn.sendall(response.encode("ascii"))

            elif orden == 'HELP':
                conn.sendall(help().encode())

            elif orden == 'RENAME_FILE':
                if len(data_list) < 3:
                    response = "RENAME_ERROR"
                else:
                    fichero = data_list[1]
                    nuevo_nombre = data_list[2]
                    response = renombrar_fichero(fichero, nuevo_nombre)
                conn.sendall(response.encode("ascii"))
                
            else:
                conn.sendall("UNKNOWN_COMMAND".encode("ascii"))
            #--EXTRA--
            """"
            elif orden == 'LOGIN':

                response=iniciar_sesion(usuario, contrasenia)
                #Comprobar si se inició sesión
                #Si es correcto, actualizar ruta del usuario y actualizar response a SUCCESS
                return response
            
            elif orden == 'SING_IN':

                response=registrar_usuario(usuario, contrasenia, confirmacion)
                
            elif orden == 'SHARE':
                
                response=compartir_fichero(fichero, usuario)
            
            #ENVIO DE INFORMACIÓN AL CLIENTE

            #Enviar información de la variable response codificada con send(response)
            #Codificarla previamente con encode(codificación) en ascii
            """
            
        except ConnectionResetError:
            print('Error: conexión cerrada en el otro extremo')
        #Cerrar conexión -> close()
        conn.close()
    print('Cerrando el servidor')
    
    #Cerrar socket -> close()
    servidor.close()