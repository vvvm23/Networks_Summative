import socket
import sys

# Encodes command and parameters then sends. Then waits for response.
def send_request(command, params, socket):
    nb_params = len(params)

    # Sending Request
    if command == "GET_BOARDS":
        if not nb_params == 0:
            print(f"ERROR:\t\tInvalid invalid number of parameters. Expected 0, got {nb_params}")
            return "INVALID_NB_PARAM"
        
        socket.send(command.encode())

    elif command == "GET_MESSAGES":
        if not nb_params == 1:
            print(f"ERROR:\t\tInvalid invalid number of parameters. Expected 1, got {nb_params}")
            return "INVALID_NB_PARAM"

        request = command
        request += f";{params[0]}"
        socket.send(request.encode())

    elif command == "POST_MESSAGE":
        if not nb_params == 3:
            print(f"ERROR:\t\tInvalid invalid number of parameters. Expected 3, got {nb_params}")
            return "INVALID_NB_PARAM"
        request = command
        
        request += f";{params[0]}"
        request += f";{params[1]}"
        request += f";{params[2]}"
        socket.send(request.encode())
    else:
        print(f"ERROR:\t\tUnknown command '{command}'")
        return "UNKNOWN_COMMAND"

    # Await and then handle response
    response = socket.recv(4096).decode()
    response_fields = response.split(';')

    # close socket in calling function
    return response_fields

# This function should handle the results of all responses. including printing
# Should not need to return anything
def handle_response(command, response_fields):

    if command == "GET_BOARDS":
        pass
    elif command == "GET_MESSAGES":
        pass
    elif command == "POST_MESSAGE":
        print("Successfully posted message to board.")
    else:
        pass

# Connected to server. Returns socket object
def connect(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    return client_socket

if __name__ == '__main__':
    pass