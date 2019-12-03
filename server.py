import sys # Get system arguments.
import os # For getting list of dirs and files
import socket # For socket programming
import time # For getting time for filename generation
import json # For encoding messages
import threading
import _thread

lock = threading.Lock()

class Logger:
    def __init__(self, log_file):
        self.log_file = log_file # Set log file path

    def write(self, command, success, address, port):
        try:
            f = open(self.log_file, mode='a') # Append if it already exists
            # Write a log entry using this lovely line of code
            f.write(f"{address}:{port}\t{time.strftime('%d/%m/%Y %H:%M:%S')}\t{command}\t{'OK' if success else 'Error'}\n")
            f.close() # Close the file so we can view the update to the log immediately
        except Exception as e:
            print("ERROR:\tFailed to write to logger.")
            print(e)

class Server: # requires socket
    def __init__(self, listen_ip, server_port, is_logging=True):
        self.server_port = server_port # Listening server port
        self.listen_ip = listen_ip # IP to listen on
        self.buffer_size = 4096 # Receive message buffer size
        self._generate_board_list() # Generate dict of boards
        self._bind() # Bind to server_port
        self.logger = Logger("server.log") if is_logging else None # Create logger file

    # Generates list of boards
    def _generate_board_list(self):
        self.board_list = {}
        for root, dirs, _ in os.walk('./board/'):
            for d in dirs:
                self.board_list[f"{d}".replace('_', ' ')] = f"{root}{d}/"
            break

    # Bind socket to server port
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

    # Start listening Loop and call functions to handle incoming requests
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

            lock.acquire()
            print(f"Received connection from {address}")
            #code = self.handle(connection_socket)
            #t_code = ["ERROR_GENERIC"]
            _thread.start_new_thread(self._thread_handle, (connection_socket,))
            #code = t_code[0]

            #if not code == "SUCCESS":
            #    print(f"ERROR:\t\t{code}")
            #connection_socket.close()
            print(f"Closed connection from {address}")

    def _thread_handle(self, socket):
        code = self.handle(socket)
        if not code == "SUCCESS":
            print(f"ERROR:\t\t{code}")
        socket.close()
        lock.release()

    # Function to handle incoming requests
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

        if command == "GET_BOARDS": # If request is for getting names of all boards
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

        elif command == "GET_MESSAGES": # If request is for getting all messages in a board
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
            response["MESSAGES"] = [] #  Array of (title, message) tuples

            if not os.path.isdir(f"./{self.board_list[board_title]}"):
                print("ERROR\t\tRequested board is missing")
                response["CODE"] = "FAIL"
                response["ERROR_MESSAGE"] = f"Requested board is missing"
                connection_socket.send(json.dumps(response).encode())
                self.logger.write(command, False, *connection_socket.getpeername())
                return "MISSING_BOARD"

            for root, _, files in os.walk(f"./{self.board_list[board_title]}"):
                # Strips /, returns last portion (to get file name), splits by - and returns date, before rejoining.
                # Gets time value in milliseconds and uses to sort in reverse order
                try:
                    files.sort(key=lambda x: time.strptime('-'.join(x.split('/')[-1].split('-')[:2]), "%Y%m%d-%H%M%S"), reverse=True)
                except:
                    print("ERROR:\t\tInvalid message format")
                    response["CODE"] = "FAIL"
                    response["ERROR_MESSAGE"] = "Invalid message format"
                    connection_socket.send(json.dumps(response).encode())
                    self.logger.write(command, False, *connection_socket.getpeername())
                    return "INVALID_MESSAGE"

                for i, f in enumerate(files):
                    if i > 99: # Only print first 100
                        break
                
                    # Open file and add contents to response. Then close file.
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

            connection_socket.send(json.dumps(response).encode())
            self.logger.write(command, True, *connection_socket.getpeername())
            return "SUCCESS"

        elif command == "POST_MESSAGE": # If request is for posting a message to a given board
            if not nb_req_fields == 4:
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

            if not os.path.isdir(f"./{self.board_list[board_title]}"):
                print("ERROR\t\tRequested board is missing")
                response["CODE"] = "FAIL"
                response["ERROR_MESSAGE"] = f"Requested board is missing"
                connection_socket.send(json.dumps(response).encode())
                self.logger.write(command, False, *connection_socket.getpeername())
                return "MISSING_BOARD"

            response["CODE"] = "SUCCESS"
            message_title = request["TITLE"].replace(' ', '_')
            message = request["MESSAGE"].replace(' ', '_') 

            # Format filename as requested
            file_time = time.strftime("%Y%m%d-%H%M%S")
            file_name = f"{file_time}-{message_title}"

            # Create and write message to file. Then close.
            try:
                # Could be susceptible to directory traversal
                fh = open(f"{self.board_list[board_title]}{file_name}", mode='w')
                fh.write(message)
                fh.close()
            except Exception as e:
                print(f"ERROR:\tFailed to write to file {self.board_list[board_title]}{file_name}")
                print(e)
                response["CODE"] = "FAIL"
                response["ERROR_MESSAGE"] = f"Failed to write message!"
                connection_socket.send(json.dumps(response).encode())
                return "WRITE_FAIL"

            connection_socket.send(json.dumps(response).encode())
            self.logger.write(command, True, *connection_socket.getpeername())
            return "SUCCESS"

        else: # If the request command is not recognised
            print("ERROR\t\tRequested Command does not exist")
            response["CODE"] = "FAIL"
            response["ERROR_MESSAGE"] = f"Requested command does not exist"
            connection_socket.send(json.dumps(response).encode())
            self.logger.write(command, False, *connection_socket.getpeername())
            return "UNKNOWN_COMMAND"

if __name__ == '__main__':
    if not len(sys.argv) == 3:
        print("Incorrect Syntax!")
        print("Usage: python server.py IP PORT")

    ip_address = sys.argv[1]
    port = int(sys.argv[2])
    if port < 1 or port > 65535:
        print("ERROR:\tPort must be in range 0-65535.")
        print("Terminating..")
        exit()

    server = Server(ip_address, port)
    server.listen()