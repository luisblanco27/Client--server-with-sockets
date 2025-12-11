import socket # Para usar sockets TCP
import sys # Para admitir argumentos por línea de comandos
import argparse as ap # Para facilitar el parseo de dichos argumentos. Usamos alias ap
import os #para ficheros

def leer_fichero(nombre_fichero):
    try:
        fichero=open(nombre_fichero,'rb')
        return (True, fichero.read())
    except:
        return (False, b'')

if __name__ == '__main__':
    # Lista de comandos
    command_list = ("LIST_FILES", 
                    "DOWNLOAD_FILE", 
                    "DELETE_FILE", 
                    "UPLOAD_FILE",
                    "MOVE_FILE",
                    "CREATE_DIR",
                    "DELETE_DIR",
                    "LIST_DIR",
                    "HELP",
                    "RENAME_FILE",
                    #--EXTRA--
                    "LOGIN",
                    "SING_IN",
                    "SHARE",
                    "SHUTDOWN"    #comando que se proporciona al alumno
                    )
  
    # Definimos el parseador. Por convenio, los argumentos opcionales se encabezan con '--'
    # Para más información, consulte https://docs.python.org/3/howto/argparse.html
    parser = ap.ArgumentParser(prog=sys.argv[0], description='Un cliente TCP de hola mundo')
    parser.add_argument('--ip', help='IP del servidor', default="127.0.0.1") # Por defecto usamos localhost
    # Los puertos por defecto están en el rango 0-1023. Podemos usar puertos a partir de ahí
    parser.add_argument('--puerto', type=int, help='Puerto TCP de salida [1024-65535]', default=5005, choices=range(1024,65535), metavar='PUERTO (1024-65535)') 
    parser.add_argument('--tam_buf',  type=int, help='Longitud del buffer interno', default=4096)
    parser.add_argument('comando', nargs="+", help='Comando a ejecutar', default='LIST_FILES')
    
    # Parseamos los argumentos de acuerdo al parser
    args = parser.parse_args(sys.argv[1:]) 
    
    # Miramos si los argumentos son correctos
    comando = args.comando
    comando[0] = comando[0].upper()
    #Comprobar que todos los comandos están bien escritos antes de enviarlo. Ejemplo para los comandos 1 a 3:
    if comando[0] in command_list[1:3]:
      if len(comando) != 2:
        print ("Error: debes de indicar el archivo en la opción", comando[0])
        sys.exit(-1)
    
    #EMPIEZA A COMPROBAR A PARTIR DE AQUÍ

    # Definimos socket e intentamos conectarnos al servidor. Para más información consulte: https://wiki.python.org/moin/HowTo/Sockets
    # Primero definimos el socket (SOCK_STREAM es TCP) usa direcciones de internet (AF_INET) -> socket(family, type, protocolo(por defecto es TCP no es necesario especificar))
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Intentamos conectarnos al servidor en el puerto especificado -> connect(ip, port)
    cliente.connect((args.ip, args.puerto))
    # Una vez conectados, debemos definir el protocolo del programa. 
    # En este caso simple, el cliente manda un mensaje al que el servidor hace ECHO.

    comando_concat = ' '.join(comando) # Concatenamos el mensaje con espacios en medio

    print ("Mandando el comando:", comando_concat, 'a la IP:', args.ip)
    
    #Enviar comando con send(comando)
    #Previamente hay que codificarlo en ascii
    cliente.send(comando_concat.encode('ascii'))
    
     # Esperamos la respuesta del servidor -> recv(buffer) recibimos la respuesta en el buffer declarado anteriormente en args

    # Consideramos cada caso en particular para interpretar la respuesta.
    if comando[0] == command_list[0]:  # Primer caso: LIST_FILES
      data = cliente.recv(args.tam_buf)
      #Comprobar la información recibida del comando LIST_FILES
      respuesta = data.decode("ascii")
      #Pintar información
      print("Respuesta del servidor:\n", respuesta)
      
      
    
    elif comando[0] == command_list[1]: #Segundo caso: DOWNLOAD_FILE
      if len(comando) > 1:
        fichero = comando[1]
        try:
            #Recibir longitud del fichero
            longitud_str = cliente.recv(args.tam_buf).decode("ascii")
            if "Error" in longitud_str:
                print(longitud_str)
            else:
                longitud = int(longitud_str)
                print(f"Tamaño recibido: {longitud} bytes")

                #Enviar ACK
                cliente.send("ACK".encode("ascii"))

                #Recibir contenido
                recv_bytes = b""
                while len(recv_bytes) < longitud:
                    bloque = cliente.recv(args.tam_buf)
                    if not bloque:
                        break
                    recv_bytes += bloque

                #Comprobar y escribir en disco
                if len(recv_bytes) == longitud:
                    print("Descargado correctamente")
                    nombre_local = os.path.basename(fichero)
                    with open(nombre_local, "wb") as f:
                        f.write(recv_bytes)
                    print(f"Fichero '{fichero}' guardado en la ruta actual")
                else:
                    print("No se pudo descargar")

        except Exception as e:
            print("ERROR")
      else:
        print("ERROR")
          
    elif comando[0] == command_list[2]:   #Tercer caso: DELETE_FILE
      if len(comando) > 1:
        try:
            respuesta = cliente.recv(args.tam_buf).decode("ascii")
            print("Respuesta del servidor:", respuesta)
        except Exception as e:
            print(f"Error en DELETE_FILE: {e}")
      else:
        print("Error: Debes especificar un nombre de fichero.")

    elif comando[0] == command_list[3]:   # Cuarto caso: UPLOAD_FILE
      if len(comando) > 1:
        fichero = comando[1]
        try:
            # 1) Comprobar el primer UPLOAD_ACK
            ack1 = cliente.recv(args.tam_buf).decode("ascii").strip()
            if ack1 != "UPLOAD_ACK":
                print("Error: no se recibió UPLOAD_ACK inicial.")
            else:
                # Leer el fichero
                with open(fichero, "rb") as f:
                    contenido = f.read()

                # 2) Mandar la longitud del contenido
                tam = str(len(contenido))
                cliente.sendall(tam.encode("ascii"))

                # 3) Recibir el segundo UPLOAD_ACK
                ack2 = cliente.recv(args.tam_buf).decode("ascii").strip()
                if ack2 != "UPLOAD_ACK":
                    print("Error: no se recibió UPLOAD_ACK tras tamaño.")
                else:
                    # 4) Enviar el contenido
                    cliente.sendall(contenido)

                    # 5) Esperar confirmación de recepción de datos
                    confirm = cliente.recv(args.tam_buf).decode("ascii").strip()
                    mensajes = confirm.split("\n")
                    for msg in mensajes:
                        if msg == "DATA_RECEIVED":
                            print("Confirmación recibida")
                        elif msg.startswith("SUCCESS"):
                            print(msg)

        except FileNotFoundError:
            print(f"Error: el fichero '{fichero}' no existe en el cliente.")
        except Exception as e:
            print(f"Error en UPLOAD_FILE: {e}")
      else:
        print("Error: Debes especificar un nombre de fichero.")


    elif comando[0] == command_list[4]:  # Quinto caso: MOVE_FILE
      if len(comando) > 2:
          origen = comando[1]
          destino = comando[2]
          try:
              respuesta = cliente.recv(args.tam_buf).decode("ascii")
              if "SUCCESS" in respuesta:
                  print(f"Fichero '{origen}' movido correctamente a '{destino}'.")
              else:
                  print("Error al mover el fichero:", respuesta)

          except Exception as e:
              print(f"Error en MOVE_FILE: {e}")
      else:
          print("Error: Debes especificar fichero y destino.")

    elif comando[0] == command_list[5]: #Sexto caso: CREATE_DIR
      data = cliente.recv(args.tam_buf)
      respuesta = data.decode("ascii")
      if "SUCCESS" in respuesta:
        print("Directorio creado correctamente.")
      else:
        print("Error al crear el directorio:", respuesta)

    elif comando[0] == command_list[6]: #Séptimo caso: DELETE_DIR
      data = cliente.recv(args.tam_buf)
      respuesta = data.decode("ascii")
      if "SUCCESS" in respuesta:
        print("Directorio eliminado correctamente.")
      else:
        print("Error al eliminar el directorio:", respuesta)

    elif comando[0] == command_list[7]: #Octavo caso: LIST_DIR
      data = cliente.recv(args.tam_buf)
      #Comprobar la información recibida 
      respuesta = data.decode("ascii")
      #Pintar información
      print("Respuesta del servidor:\n", respuesta)

    elif comando[0] == command_list[8]: #Noveno caso: HELP
      try:
        # El comando ya se envió de forma genérica antes
        respuesta = cliente.recv(args.tam_buf).decode("ascii")

        # Comprobar información recibida
        if respuesta:
            print("=== AYUDA DEL SERVIDOR ===")
            print(respuesta)
        else:
            print("No se recibió información de ayuda.")
      except Exception as e:
        print(f"Error al recibir la ayuda: {e}")
    elif comando[0] == command_list[9]: #Noveno caso: RENAME_FILE
      respuesta = cliente.recv(args.tam_buf).decode("ascii")
      print("Respuesta del servidor:", respuesta)
    
      
    #--EXTRA--
    # elif comando[0] == command_list[9]: #Décimo caso: LOGIN
    # 
    #   #Comprobar información recibida 
    #   #informar al usuario del inicio de sesión
    # 
    # elif comando[0] == command_list[10]: #Undécimo caso: SING_IN
    #   #Comprobar información recibida
    #   #Informar al usuario del registro
    #
    # elif comando[0] == command_list[11]: #Duodécimo caso: SHARE
    #   #Comprobar información recibida
    #   #Informar al usuario de que la acción se realizó satisfactoriamente
    
    elif comando[0] == command_list[12]: #SHUTDOWN
      print("Servidor apagado")
    
    else: #Decimo caso: UNKNOWN_COMMAND
      respuesta = cliente.recv(args.tam_buf).decode("ascii")
      print(respuesta)
    # Enviamos la respuesta al cliente
    # Una vez acabado el intercambio de datos, debemos cerrar el socket
    # Cerramos el socket -> close()
    cliente.close()
