import socket # For socket programming
import sys # For getting system arguments
import json # For encoding messages

# Encodes command and parameters then sends. Then waits for response.
def send_request(command, client_socket, params=[]):
    nb_params = len(params)
    request = {}

    # Sending Request
    # Before sending, we will convert to json then encode further
    if command == "GET_BOARDS":
        if not nb_params == 0:
            print(f"ERROR:\t\tInvalid invalid number of parameters. Expected 0, got {nb_params}")
            return "INVALID_NB_PARAM"
        
        request["COMMAND"] = "GET_BOARDS" # Command parameter
        client_socket.send(json.dumps(request).encode())

    elif command == "GET_MESSAGES":
        if not nb_params == 1:
            print(f"ERROR:\t\tInvalid invalid number of parameters. Expected 1, got {nb_params}")
            return "INVALID_NB_PARAM"

        request["COMMAND"] = "GET_MESSAGES" # Command parameter
        request["BOARD"] = params[0] # Board name to get parameter
        client_socket.send(json.dumps(request).encode())

    elif command == "POST_MESSAGE":
        if not nb_params == 3:
            print(f"ERROR:\t\tInvalid invalid number of parameters. Expected 3, got {nb_params}")
            return "INVALID_NB_PARAM"
        request["COMMAND"] = command # Command parameter
        request["BOARD"] = params[0] # Board name to write to parameter
        request["TITLE"] = params[1].replace(' ', '_') # Message title parameter
        request["MESSAGE"] = params[2].replace(' ', '_') # Message body parameter

        client_socket.send(json.dumps(request).encode())
    else: # Unknown command, do not send anything.
        print(f"ERROR:\t\tUnknown command '{command}'")
        return "UNKNOWN_COMMAND"

    # Await and then handle response
    try:
        response = json.loads(client_socket.recv(4096).decode()) # Decode in same way as before
    except socket.timeout:
        print("ERROR:\tConnection timed out after 10 seconds.")
        return "CONNECTION_TIMEOUT"
    except:
        raise

    # close socket in calling function
    return response

# This function should handle the results of all responses. including printing
def handle_response(command, response):

    if not response["CODE"] == "SUCCESS":
        print("ERROR:\tAn error occured while handling the request")
        print(f"ERROR:\t{response['ERROR_MESSAGE']}")
        return

    if command == "GET_BOARDS": # Handles response to GET_BOARDS, printing board names nicely
        print("Available Boards:")
        print('\n'.join(f"\t{i+1}. {b.replace('_', ' ')}" for i, b in enumerate(response["BOARDS"])))
        boards_dict = {}
        for i, b in enumerate(response["BOARDS"]):
            boards_dict[str(i+1)] = b
        return boards_dict

    elif command == "GET_MESSAGES": # Handles response to GET_MESSAGES, printing messages nicely
        print('\n'.join(f"{m[0].replace('_', ' ')}:\n\t{m[1].replace('_', ' ')}" for m in response["MESSAGES"]))

    elif command == "POST_MESSAGE": # Simply informs the user the message was posted successfully.
        print("Successfully posted message to board.")
    else: # Unknown response command, so just discard.
        print("ERROR:\tUnknown command.")
        
# Connected to server. Returns socket object
def connect(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.settimeout(10.0) # Timeout after 10 seconds
        client_socket.connect((server_ip, server_port))
    except ConnectionRefusedError:
        print("ERROR:\tNo connection established. Target machine refused.")
        return
    except OSError:
        print("ERROR:\tNo connection established. Unreachable network.")
        return
    except OverflowError:
        print("ERROR:\tPort must be in range 0-65535.")
        return
    except socket.timeout:
        print("ERROR:\tConnection timed out after 10 seconds.")
        return
    except:
        raise

    return client_socket

# Main function to display menu, handle inputs and pass responses and requests to other functions
def display_menu(server_ip, server_port):
    if server_port < 1 or server_port > 65535:
        print("ERROR:\tPort must be in range 0-65535.")
        print("Terminating..")
        exit()

    # Attempt to connect to server
    client_socket = connect(server_ip, server_port)
    if not client_socket:
        print("Terminating..")
        exit()

    # Get the list of boards as the first request
    response = send_request("GET_BOARDS", client_socket)
    if not type(response) == dict:
        if client_socket:
            client_socket.close()
        print("Terminating..")
        exit() # Failed at first request. Terminating as we cannot continue.

    boards_dict = handle_response("GET_BOARDS", response)
    client_socket.close()

    # Enter menu loop
    while True:
        # Display menu options and get input
        print("\nX - Where X is a number in the list to view this board")
        print("POST - Post a message to a board.")
        print("QUIT - Close the program")
        user_input = input("> ")
        
        if user_input == "QUIT": # Break menu loop
            print("Terminating.. Thanks for coming.")
            break
        elif user_input == "POST": # Post a message to a board. Start wizard for this.
            post_params = []
            print("Enter board number:")
            user_input = input("> ")
            if not user_input in boards_dict:
                print("ERROR:\tBoard does not exist.")
                continue
            post_params.append(boards_dict[user_input])

            print("Enter message title:")
            user_input = input("> ")

            post_params.append(user_input)

            print("Enter message content:")
            user_input = input("> ")

            post_params.append(user_input)

            client_socket = connect(server_ip, server_port) # Attempt to connect to server
            if not client_socket:
                continue

            response = send_request("POST_MESSAGE", client_socket, post_params) # Pass to sender function
            if not type(response) == dict:
                client_socket.close()
                continue

            handle_response("POST_MESSAGE", response) # Pass response to handler function
            client_socket.close() # Close the socket

        elif user_input in boards_dict: # Get a Message from a board
            client_socket = connect(server_ip, server_port) # Attempt to connect to server
            if not socket:
                continue

            response = send_request("GET_MESSAGES", client_socket, [boards_dict[user_input]]) # Pass to sender function
            if not type(response) == dict:
                client_socket.close()
                continue

            handle_response("GET_MESSAGES", response) # Pass response to handler function
            client_socket.close() # Close the socket
        elif user_input.isdigit(): # If it is a digit, but not a digit in the board menu, reject.
            print("ERROR:\tBoard specified does not exist.")
            continue
        else: # Else, also not valid, so reject.
            print("ERROR:\tUnknown command. Please try again.")
            continue
    
    if client_socket: # If the socket still exists upon termination, close the socket.
        client_socket.close()

if __name__ == '__main__':
    if len(sys.argv) == 3:
        display_menu(sys.argv[1], int(sys.argv[2]))
    else: # If not enough arguments, inform user correct syntax.
        print("Usage: python client.py [SERVER IP] [SERVER PORT]")