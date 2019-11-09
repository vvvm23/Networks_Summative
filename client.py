import socket
import sys

# Encodes command and parameters then sends. Then waits for response.
def send_request(command, client_socket, params=[]):
    nb_params = len(params)

    # Sending Request
    if command == "GET_BOARDS":
        if not nb_params == 0:
            print(f"ERROR:\t\tInvalid invalid number of parameters. Expected 0, got {nb_params}")
            return "INVALID_NB_PARAM"
        
        client_socket.send(command.encode())

    elif command == "GET_MESSAGES":
        if not nb_params == 1:
            print(f"ERROR:\t\tInvalid invalid number of parameters. Expected 1, got {nb_params}")
            return "INVALID_NB_PARAM"

        request = command
        request += f";{params[0]}"
        client_socket.send(request.encode())

    elif command == "POST_MESSAGE":
        if not nb_params == 3:
            print(f"ERROR:\t\tInvalid invalid number of parameters. Expected 3, got {nb_params}")
            return "INVALID_NB_PARAM"
        request = command
        
        request += f";{params[0]}"
        request += f";{params[1]}"
        request += f";{params[2]}"
        client_socket.send(request.encode())
    else:
        print(f"ERROR:\t\tUnknown command '{command}'")
        return "UNKNOWN_COMMAND"

    # Await and then handle response
    try:
        response = client_socket.recv(4096).decode()
    except socket.timeout as e:
        print("ERROR:\tConnection timed out after 10 seconds.")
        return "CONNECTION_TIMEOUT"
    except:
        raise
        exit()

    response_fields = response.split(';')

    # close socket in calling function
    return response_fields

# This function should handle the results of all responses. including printing
def handle_response(command, response_fields):

    if not response_fields[0] == "SUCCESS":
            print("ERROR:\tAn error occured while handling the request")
            print(f"ERROR:\t{response_fields[1]}")
            return

    response_fields = response_fields[1:]

    if command == "GET_BOARDS":
        print("Available Boards:")
        print('\n'.join(f"\t{i+1}. {b.replace('_', ' ')}" for i, b in enumerate(response_fields)))
        boards_dict = {}
        for i, b in enumerate(response_fields):
            boards_dict[str(i+1)] = b
        return boards_dict

    elif command == "GET_MESSAGES":
        print('\n'.join(f"{m.split('-')[0].replace('_', ' ')}:\n\t{m.split('-')[1].replace('_', ' ')}" for m in response_fields))

    elif command == "POST_MESSAGE":
        print("Successfully posted message to board.")
    else:
        print("ERROR:\tUnknown command.")
        

# Connected to server. Returns socket object
def connect(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.settimeout(10.0)
        client_socket.connect((server_ip, server_port))
        #client_socket.settimeout(None)
    except ConnectionRefusedError:
        print("ERROR:\tNo connection established. Target machine refused.")
        return
    except OSError:
        print("ERROR:\tNo connection established. Unreachable network.")
        return
    except OverflowError:
        print("ERROR:\tPort must be in range 0-65535.")
        return
    except client_socket.timeout:
        print("ERROR:\tConnection timed out after 10 seconds.")
        return
    except:
        raise

    return client_socket

def display_menu(server_ip, server_port):
    if server_port < 1 or server_port > 65535:
        print("ERROR:\tPort must be in range 0-65535.")
        print("Terminating..")
        exit()

    client_socket = connect(server_ip, server_port)
    if not client_socket:
        print("Terminating..")
        exit()

    response_fields = send_request("GET_BOARDS", client_socket)
    if not type(response_fields) == list:
        if client_socket:
            client_socket.close()
        print("Terminating..")
        exit() # Failed at first request. Terminating.

    boards_dict = handle_response("GET_BOARDS", response_fields)
    client_socket.close()

    while True:
        print("\nX - Where X is a number in the list to view this board")
        print("POST - Post a message to a board.")
        print("QUIT - Close the program")
        user_input = input("> ")
        
        if user_input == "QUIT":
            print("Terminating.. Thanks for coming.")
            break
        elif user_input == "POST":
            post_params = []
            print("Enter board number:")
            user_input = input("> ")
            if not user_input in boards_dict:
                print("ERROR:\tBoard does not exist.")
                continue
            post_params.append(boards_dict[user_input])

            print("Enter message title:")
            user_input = input("> ") # implement checks on this

            post_params.append(user_input)

            print("Enter message content:")
            user_input = input("> ") # again, implement checks on this

            post_params.append(user_input)

            client_socket = connect(server_ip, server_port)
            if not client_socket:
                continue

            response_fields = send_request("POST_MESSAGE", client_socket, post_params)
            if not type(response_fields) == list:
                client_socket.close()
                continue

            handle_response("POST_MESSAGE", response_fields)
            client_socket.close()

        elif user_input in boards_dict:
            client_socket = connect(server_ip, server_port)
            if not socket:
                continue

            response_fields = send_request("GET_MESSAGES", client_socket, [boards_dict[user_input]])
            if not type(response_fields) == list:
                client_socket.close()
                continue

            handle_response("GET_MESSAGES", response_fields)
            client_socket.close()
        elif user_input.isdigit():
            print("ERROR:\tBoard specified does not exist.")
            continue
        else:
            print("ERROR:\tUnknown command. Please try again.")
            continue
    
    if client_socket:
        client_socket.close()

if __name__ == '__main__':
    if len(sys.argv) == 3:
        display_menu(sys.argv[1], int(sys.argv[2]))
    else:
        print("Usage: python client.py [SERVER IP] [SERVER PORT]")