import sys # Get system arguments.
import os # For getting list of dirs and files
import socket # For socket programming
import time # For getting time for filename generation
import json

class Logger:
    def __init__(self, log_file):
        self.log_file = log_file

    def write(self, command, success, address, port):
        try:
            f = open(self.log_file, mode='a')
            f.write(f"{address}:{port}\t{time.strftime('%d/%m/%Y %H:%M:%S')}\t{command}\t{'OK' if success else 'Error'}\n")
            f.close()
        except Exception as e:
            print("ERROR:\tFailed to write to logger.")
            print(e)


class Server: # requires socket
    def __init__(self, listen_ip, server_port):
        self.server_port = server_port
        self.listen_ip = listen_ip
        self.buffer_size = 1024
        self._generate_board_list() # Generate dict of boards
        self._bind() # Bind to server_port
        self.logger = Logger("server.log")

    def _generate_board_list(self):
        self.board_list = {}
        for root, dirs, _ in os.walk('./board/'):
            for d in dirs:
                self.board_list[f"{d}".replace('_', ' ')] = f"{root}{d}/"
            break

    def _bind(self):
        print(f"Creating socket at port {self.server_port}.. ", end='')
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.listen_ip, self.server_port))
        except Exception as e:
            print("Failure.\nERROR:\tFailed to create socket.")
            print(e)
            print("Terminating..")
            exit()
        print("Done.")

    def listen(self):
        if not self.server_socket:
            print("ERROR:\t\tSocket not bound! Terminating!")
            exit()

        print(f"Starting Server Listening.. ", end='')
        try:
            self.server_socket.listen(1)
        except Exception as e:
            print("Failure.\nERROR:\tFailed to start listening.")
            print(e)
            print("Terminating..")
            exit()
        print("Done.")

        print("Entering Server Loop.")
        while True:
            try:
                connection_socket, address = self.server_socket.accept()
            except Exception as e:
                print("ERROR:\tFailed to accept connection!")
                print(e)
                continue

            print(f"Received connection from {address}")
            code = self.handle(connection_socket)
            if not code == "SUCCESS":
                print(f"ERROR:\t\t{code}")
            connection_socket.close()
            print(f"Closed connection from {address}")

    def handle(self, connection_socket):
        # Receive and split incoming message
        try:
            request = json.loads(connection_socket.recv(self.buffer_size).decode())
        except socket.timeout as e:
            print("ERROR:\tConnection timed out after 10 seconds.")
            return "CONNECTION_TIMEOUT"
        except Exception as e:
            print("ERROR:\tFailed to receive incoming connection.")
            print(e)
            return "ERROR_GENERIC"

        response = {}

        nb_req_fields = len(request) # For checking in nb. parameters correct
        command = request["COMMAND"]

        if command == "GET_BOARDS":
            if not nb_req_fields == 1:
                print("ERROR:\t\tInvalid number of fields in request!")
                response["CODE"] = "FAIL"
                response["ERROR_MESSAGE"] = f"Invalid number of fields for GET_BOARDS. Expected 1 got {nb_req_fields}"
                connection_socket.send(json.dumps(response).encode())
                self.logger.write(command, False, *connection_socket.getpeername())
                return "INVALID_NB_REQ"

            response["CODE"] = "SUCCESS"
            # Iterate through board titles and add to response.
            response["BOARDS"] = []
            for title in self.board_list:
                response['BOARDS'].append(f"{title.replace(' ', '_')}")

            connection_socket.send(json.dumps(response).encode())
            self.logger.write(command, True, *connection_socket.getpeername())
            return "SUCCESS"

        elif command == "GET_MESSAGES":
            if not nb_req_fields == 2:
                print("ERROR\t\tInvalid number of fields in request!")
                response["CODE"] = "FAIL"
                response["ERROR_MESSAGE"] = f"Invalid number of fields for GET_MESSAGES. Expected 2 got {nb_req_fields}"
                connection_socket.send(json.dumps(response).encode())
                self.logger.write(command, False, *connection_socket.getpeername())
                return "INVALID_NB_REQ"

            board_title = request["BOARD"].replace('_', ' ')

            if not board_title in self.board_list:
                print("ERROR\t\tRequested board does not exist")
                response["CODE"] = "FAIL"
                response["ERROR_MESSAGE"] = f"Requested board does not exist"
                connection_socket.send(json.dumps(response).encode())
                self.logger.write(command, False, *connection_socket.getpeername())
                return "INVALID_NAME"

            response["CODE"] = "SUCCESS"
            response["MESSAGES"] = []
            for root, _, files in os.walk(f"./{self.board_list[board_title]}"):
                # Strips /, returns last portion (to get file name), splits by - and returns date, before rejoining.
                # Gets time value in milliseconds and uses to sort in reverse order
                files.sort(key=lambda x: time.strptime('-'.join(x.split('/')[-1].split('-')[:2]), "%Y%m%d-%H%M%S"), reverse=True)

                for i, f in enumerate(files):
                    # Open file and add contents to response. Then close file.
                    #f = f"{root}{self.board_list[board_title]}{f}"

                    try:
                        f = f"{root}{f}"
                        fh = open(f)
                        f_contents = fh.read()
                        fh.close()
                    except:
                        print("ERROR:\tFailed to read file {root}{f}")
                        print(e)
                        continue

                    message_title = f.split('-')[2] # Append title before contents delimited with '-'
                    response["MESSAGES"].append((message_title.replace(' ', '_'), f_contents.replace(' ', '_')))

                    if i > 99:
                        break
                    #break

            connection_socket.send(json.dumps(response).encode())
            self.logger.write(command, True, *connection_socket.getpeername())
            return "SUCCESS"

        elif command == "POST_MESSAGE":
            if not nb_req_fields == 4: #maybe remove for ; in message? or make < and concat further fields
                print("ERROR\t\tInvalid number of fields in request!")
                response["CODE"] = "FAIL"
                response["ERROR_MESSAGE"] = f"Invalid number of fields for POST_MESSAGE. Expected 4 got {nb_req_fields}"
                
                connection_socket.send(json.dumps(response).encode())
                self.logger.write(command, False, *connection_socket.getpeername())
                return "INVALID_NB_REQ"

            board_title = request["BOARD"].replace('_', ' ')

            if not board_title in self.board_list:
                print("ERROR\t\tRequested board does not exist")
                response["CODE"] = "FAIL"
                response["ERROR_MESSAGE"] = f"Requested board does not exist"
                connection_socket.send(json.dumps(response).encode())
                self.logger.write(command, False, *connection_socket.getpeername())
                return "INVALID_NAME"

            response["CODE"] = "SUCCESS"
            message_title = request["TITLE"].replace(' ', '_')
            message = request["MESSAGE"].replace(' ', '_') 

            # Format filename as requested
            file_time = time.strftime("%Y%m%d-%H%M%S")
            file_name = f"{file_time}-{message_title}"

            # Create and write message to file. Then close.
            # Obviously susceptible to path traversal
            try:
                # Could be susceptible to directory traversal
                fh = open(f"{self.board_list[board_title]}{file_name}", mode='w')
                fh.write(message)
                fh.close()
            except Exception as e:
                print("ERROR:\tFailed to write to file {self.board_list[board_title]}{file_name}")
                print(e)
                response["CODE"] = "FAIL"
                response["ERROR_MESSAGE"] = f"Failed to write message!"
                connection_socket.send(json.dumps(response).encode)
                return "WRITE_FAIL"

            connection_socket.send(json.dumps(response).encode())
            self.logger.write(command, True, *connection_socket.getpeername())
            return "SUCCESS"

        else:
            print("ERROR\t\tRequested Command does not exist")
            response["CODE"] = "FAIL"
            response["ERROR_MESSAGE"] = f"Requested command does not exist"
            connection_socket.send(json.dumps(response).encode())
            self.logger.write(command, False, *connection_socket.getpeername())
            return "UNKNOWN_COMMAND"

if __name__ == '__main__':
    server = Server(sys.argv[1], int(sys.argv[2])) # validate this.
    server.listen()