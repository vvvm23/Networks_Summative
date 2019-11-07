import sys # Get system arguments.
import os # For getting list of dirs and files
import socket # For socket programming
import time # For getting time for filename generation

class Server: # requires socket
    def __init__(self, server_port):
        self.server_port = server_port
        self.buffer_size = 4096
        self._generate_board_list() # Generate dict of boards
        self._bind() # Bind to server_port

    def _generate_board_list(self):
        self.board_list = {}
        for root, dirs, _ in os.walk('./board/'):
            for d in dirs:
                self.board_list[f"{d}".replace('_', ' ')] = f"{root}{d}/"
            break
        print(self.board_list)

    def _bind(self):
        print(f"Creating socket at port {self.server_port}.. ", end='')
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('', self.server_port))
        print("Done.")

    def listen(self):
        if not self.server_socket: # Does this catch if server_socket does not exist?
            print("ERROR:\t\tSocket not bound! Terminating!")
            exit()

        print(f"Starting Server Listening.. ", end='')
        self.server_socket.listen(1)
        print("Done.")

        print("Entering Server Loop.")
        while True:
            connection_socket, address = self.server_socket.accept()
            print(f"Received connection from {address}")
            code = self.handle(connection_socket)
            if not code == "SUCCESS":
                print(f"ERROR:\t\t{code}")
            connection_socket.close()
            print(f"Closed connection from {address}")

    def handle(self, connection_socket):
        # Receive and split incoming message
        request_string = connection_socket.recv(self.buffer_size).decode()
        request_fields = request_string.split(';')

        response = ""

        nb_req_fields = len(request_fields) # Fpr checking in nb. parameters correct
        command = request_fields[0]

        if command == "GET_BOARDS":
            if not nb_req_fields == 1:
                print("ERROR:\t\tInvalid number of fields in request!")
                response = f"FAIL;Invalid number of fields for GET_BOARDS. Expected 1 got {nb_req_fields}"
                connection_socket.send(response.encode())
                return "INVALID_NB_REQ"

            response += "SUCCESS"
            # Iterate through board titles and add to response. Delimit with ;
            for title in self.board_list:
                response += f";{title}"

            connection_socket.send(response.encode())
            return "SUCCESS"

        elif command == "GET_MESSAGES":
            if not nb_req_fields == 2:
                print("ERROR\t\tInvalid number of fields in request!")
                response = f"FAIL;Invalid number of fields for GET_MESSAGES. Expected 2 got {nb_req_fields}"
                connection_socket.send(response.encode())
                return "INVALID_NB_REQ"

            board_title = request_fields[1]

            if not board_title in self.board_list:
                print("ERROR\t\tRequested board does not exist")
                response = f"FAIL;Requested board does not exist"
                connection_socket.send(response.encode())
                return "INVALID_NAME"

            response += "SUCCESS"

            # TODO: Sort by most recent 100
            for root, _, files in os.walk(f"./{self.board_list[board_title]}"):
                for i, f in enumerate(files):
                    # Open file and add contents to response. Then close file.
                    f = f"{root}{self.board_list[board_title]}{f}"
                    fh = open(f)
                    f_contents = fh.read()
                    fh.close()

                    message_title = f.split('-')[2] # Append title before contents delimited with '-'
                    response += f";{message_title}-{f_contents}"

                    if i > 99:
                        break
                    break

            connection_socket.send(response.encode())
            return "SUCCESS"

        elif command == "POST_MESSAGE":
            if not nb_req_fields == 4: #maybe remove for ; in message? or make < and concat further fields
                print("ERROR\t\tInvalid number of fields in request!")
                response = f"FAIL;Invalid number of fields for POST_MESSAGE. Expected 4 got {nb_req_fields}"
                connection_socket.send(response.encode())
                return "INVALID_NB_REQ"

            board_title = request_fields[1]

            if not board_title in self.board_list:
                print("ERROR\t\tRequested board does not exist")
                response = f"FAIL;Requested board does not exist"
                connection_socket.send(response.encode())
                return "INVALID_NAME"

            response += "SUCCESS"
            message_title = request_fields[2].replace(' ', '_')
            message = request_fields[3] # sanitise this

            # Format filename as requested
            file_time = time.strftime("%Y%m%d-%H%M%S")
            file_name = f"{file_time}-{message_title}"

            # Create and write message to file. Then close.
            fh.open(f"./board/{self.board_list[board_title]}{file_name}")
            fh.write(message)
            fh.close()

            connection_socket.send(response.encode())
            return "SUCCESS"

        else:
            print("ERROR\t\tRequested Command does not exist")
            response = f"FAIL;Requested command does not exist"
            connection_socket.send(response.encode())
            return "UNKNOWN_COMMAND"

if __name__ == '__main__':
    server = Server(9999)
