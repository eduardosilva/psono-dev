"""
A small demo script that shows how to export the datastore (unrestricted API key)
"""
import os
import uuid
import requests
import json
import nacl.encoding
import nacl.signing
import nacl.secret
import nacl.utils
from nacl.public import PrivateKey, PublicKey, Box
import binascii
import socket

api_key_id = os.environ.get('API_KEY_ID')
api_key_private_key = os.environ.get('API_KEY_PRIVATE_KEY')
api_key_secret_key = os.environ.get('API_KEY_SECRET_KEY')
server_url = os.environ.get('SERVER_URL')
server_public_key = os.environ.get('SERVER_PUBLIC_KEY')
server_signature = os.environ.get('SERVER_SIGNATURE')

SSL_VERIFY = False

def get_device_description():
    """
    This info is later shown in the "Open sessions" overview in the client. Should be something so the user knows where
    this session is coming from.

    :return:
    :rtype:
    """
    return 'Console Client ' + socket.gethostname()

def generate_client_login_info():
    """
    Generates and signs the login info
    Returns a tuple of the session private key and the login info

    :return:
    :rtype:
    """

    box = PrivateKey.generate()
    session_private_key = box.encode(encoder=nacl.encoding.HexEncoder).decode()
    session_public_key = box.public_key.encode(encoder=nacl.encoding.HexEncoder).decode()

    info = {
        'api_key_id': api_key_id,
        'session_public_key': session_public_key,
        'device_description': get_device_description(),
    }

    info = json.dumps(info)

    signing_box = nacl.signing.SigningKey(api_key_private_key, encoder=nacl.encoding.HexEncoder)

    # The first 128 chars (512 bits or 64 bytes) are the actual signature, the rest the binary encoded info
    signed = signing_box.sign(info.encode())
    signature = binascii.hexlify(signed.signature)

    return session_private_key, {
        'info': info,
        'signature': signature.decode(),
    }

def decrypt_server_login_info(login_info_hex, login_info_nonce_hex, session_public_key, session_private_key):
    """
    Takes the login info and nonce together with the session public and private key.
    Will decrypt the login info and interpret it as json and return the json parsed object.
    :param login_info:
    :type login_info:
    :param login_info_nonce:
    :type login_info_nonce:
    :param session_public_key:
    :type session_public_key:
    :param session_private_key:
    :type session_private_key:

    :return:
    :rtype:
    """

    crypto_box = Box(PrivateKey(session_private_key, encoder=nacl.encoding.HexEncoder),
                     PublicKey(session_public_key, encoder=nacl.encoding.HexEncoder))

    login_info = nacl.encoding.HexEncoder.decode(login_info_hex)
    login_info_nonce = nacl.encoding.HexEncoder.decode(login_info_nonce_hex)

    login_info = json.loads(crypto_box.decrypt(login_info, login_info_nonce).decode())

    return login_info

def verify_signature(login_info, login_info_signature):
    """
    Takes the login info and the provided signature and will validate it with the help of server_signature.

    Will raise an exception if it does not match.

    :param login_info:
    :type login_info:
    :param login_info_signature:
    :type login_info_signature:

    :return:
    :rtype:
    """

    verify_key = nacl.signing.VerifyKey(server_signature, encoder=nacl.encoding.HexEncoder)

    verify_key.verify(login_info.encode(), binascii.unhexlify(login_info_signature))


def decrypt_symmetric(text_hex, nonce_hex, secret):
    """
    Decryts an encrypted text with nonce with the given secret

    :param text_hex:
    :type text_hex:
    :param nonce_hex:
    :type nonce_hex:
    :param secret:
    :type secret:
    :return:
    :rtype:
    """

    text = nacl.encoding.HexEncoder.decode(text_hex)
    nonce = nacl.encoding.HexEncoder.decode(nonce_hex)

    secret_box = nacl.secret.SecretBox(secret, encoder=nacl.encoding.HexEncoder)

    return secret_box.decrypt(text, nonce)


def encrypt_symmetric(msg, secret):
    """
    Encrypts a message with a random nonce and a given secret

    :param msg: The message as str
    :type msg: str
    :param secret: The secret as hex encoded str
    :type secret: str
    :return: A dict, containing the encrypted message with the text and nonce being returned separately
    :rtype: dict
    """

    # generate random nonce
    nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)

    # open crypto box with session secret
    secret_box = nacl.secret.SecretBox(secret, encoder=nacl.encoding.HexEncoder)

    # encrypt msg with crypto box and nonce
    encrypted = secret_box.encrypt(msg.encode(), nonce)

    # cut away the nonce
    text = encrypted[len(nonce):]

    # convert nonce and encrypted msg to hex
    nonce_hex = nacl.encoding.HexEncoder.encode(nonce).decode()
    text_hex = nacl.encoding.HexEncoder.encode(text).decode()

    return {'text': text_hex, 'nonce': nonce_hex}

def decrypt_with_api_secret_key(secret_hex, secret_nonce_hex):
    """
    take anything that is encrypted with the api keys secret and decrypts it. e.g. the users secret and private key

    :param secret_hex:
    :type secret_hex:
    :param secret_nonce_hex:
    :type secret_nonce_hex:

    :return:
    :rtype:
    """

    return decrypt_symmetric(secret_hex, secret_nonce_hex, api_key_secret_key)


def api_request(method, endpoint, data = None, token = None, session_secret_key = None):

    if token:
        headers = {'content-type': 'application/json', 'authorization': 'Token ' + token}
    else:
        headers = {'content-type': 'application/json'}


    r = requests.request(method, server_url + endpoint, data=data, headers=headers, verify=SSL_VERIFY)

    if not session_secret_key:
        return r.json()
    else:
        encrypted_content = r.json()
        decrypted_content = decrypt_symmetric(encrypted_content['text'], encrypted_content['nonce'], session_secret_key)
        return json.loads(decrypted_content)


def api_login(client_login_info):
    """
    API Request: Sends the actual login

    :param client_login_info:
    :type client_login_info:

    :return:
    :rtype:
    """

    method = 'POST'
    endpoint = '/api-key/login/'
    data = json.dumps(client_login_info)

    return api_request(method, endpoint, data)


def api_read_datastores(token, session_secret_key):
    """
    Reads all datastores

    :param token:
    :type token:
    :param session_secret_key:
    :type session_secret_key:
    :return:
    :rtype:
    """

    method = 'GET'
    endpoint = '/datastore/'

    return api_request(method, endpoint, token=token, session_secret_key=session_secret_key)


def api_logout(token, session_secret_key):
    """
    Destroys the session again.

    :param token:
    :type token:
    :param session_secret_key:
    :type session_secret_key:
    :return:
    :rtype:
    """

    method = 'POST'
    endpoint = '/authentication/logout/'

    return api_request(method, endpoint, token=token, session_secret_key=session_secret_key)


def api_read_datastore(token, session_secret_key, datastore_id):
    """
    Reads the content of a specific datastore

    :param token:
    :type token:
    :param session_secret_key:
    :type session_secret_key:
    :param datastore_id:
    :type datastore_id:
    :return:
    :rtype:
    """

    method = 'GET'
    endpoint = '/datastore/' + datastore_id + '/'

    return api_request(method, endpoint, token=token, session_secret_key=session_secret_key)


def api_write_datastore(token, session_secret_key, datastore_id, encrypted_data, encrypted_data_nonce):
    """
    Updates a datastore

    :param token:
    :type token:
    :param session_secret_key:
    :type session_secret_key:
    :param datastore_id:
    :type datastore_id:
    :param encrypted_data:
    :type encrypted_data:
    :param encrypted_data_nonce:
    :type encrypted_data_nonce:
    :return:
    :rtype:
    """

    method = 'POST'
    endpoint = '/datastore/'
    data = json.dumps({
        'datastore_id': datastore_id,
        'data': encrypted_data,
        'data_nonce': encrypted_data_nonce,
    })

    return api_request(method, endpoint, data=data, token=token, session_secret_key=session_secret_key)


def api_create_secret(token, session_secret_key, encrypted_data, encrypted_data_nonce, link_id, parent_datastore_id, callback_url, callback_user, callback_pass):
    """
    Creates a secret

    :param token:
    :param session_secret_key:
    :param encrypted_data:
    :param encrypted_data_nonce:
    :param link_id:
    :param parent_datastore_id:
    :param parent_share_id:
    :param callback_url:
    :param callback_user:
    :param callback_pass:
    :return:
    """

    method = 'PUT'
    endpoint = '/secret/'
    data = json.dumps({
        'data': encrypted_data,
        'data_nonce': encrypted_data_nonce,
        'link_id': link_id,
        'parent_datastore_id': parent_datastore_id,
        'callback_url': callback_url,
        'callback_user': callback_user,
        'callback_pass': callback_pass,
    })

    return api_request(method, endpoint, data=data, token=token, session_secret_key=session_secret_key)

def create_folder_if_not_exist(folder_name, datastore_content):
    """
    Searches the datastore content for the folde rwith the specified name.
    if the folder exists it will return the folder
    If the folder doesn't exist it will create the folder and return it

    :param folder_name:
    :param datastore_content:
    :return:
    """
    if 'folders' not in datastore_content:
        datastore_content['folders'] = []

    for f in datastore_content['folders']:
        if f['name'] == folder_name:
            return f

    folder = {
        'id': str(uuid.uuid4()),
        'name': folder_name,
    }

    datastore_content['folders'].append(folder)

    return folder

def create_secret(
        token,
        session_secret_key,
        name,
        type,
        content,
        folder,
        datastore_id,
):
    """
    Creates a new secret and adds it to the folder

    :param token:
    :param session_secret_key:
    :param name:
    :param type:
    :param content:
    :param folder:
    :return:
    """
    if 'items' not in folder:
        folder['items'] = []

    secret_key = nacl.encoding.HexEncoder.encode(nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)).decode()
    encrypted_secret = encrypt_symmetric(json.dumps(content), secret_key)

    link_id = str(uuid.uuid4())

    result = api_create_secret(
        token, session_secret_key, encrypted_secret['text'], encrypted_secret['nonce'], link_id, datastore_id,
        '', '', ''
    )

    item = {
        'id': link_id,
        'name': name,
        'type': type,
        'secret_id': result['secret_id'],
        'secret_key': secret_key,
    }

    folder['items'].append(item)


def main():
    # 1. Generate the login info including the private key for PFS
    session_private_key, client_login_info = generate_client_login_info()

    # 2. Send the login request and handle eventual exceptions, problems and so on ...
    json_response = api_login(client_login_info)

    # 3. Verify the signature in order to proof that we are really communicating with the server
    # (or someone who is in the posession of the servers private key :D)
    verify_signature(json_response['login_info'], json_response['login_info_signature'])

    # 4. Decrypt the actual login info with the token and session_secret_key for the transport encryption
    decrypted_sever_login_info = decrypt_server_login_info(json_response['login_info'], json_response['login_info_nonce'], json_response['server_session_public_key'], session_private_key)

    token = decrypted_sever_login_info['token'] # That is the token that we have to send always as header
    session_secret_key = decrypted_sever_login_info['session_secret_key'] # that is the symmetric secret for the transport encryption

    if decrypted_sever_login_info['api_key_restrict_to_secrets']:
        print("api key is restricted. it should only be used to read specific secrets")
        return
    if not decrypted_sever_login_info['api_key_read']:
        print("api key doesn't allow read. Please allow read first")
        return

    if not decrypted_sever_login_info['api_key_write']:
        print("api key doesn't allow write. Please allow write first")
        return

    # if the api key is unrestricted then the request will also return the encrypted secret and private key of the user, symmetric encrypted with the api secret key
    user_secret_key = decrypt_with_api_secret_key(decrypted_sever_login_info['user']['secret_key'], decrypted_sever_login_info['user']['secret_key_nonce']) # The user's secret key

    # 5. Now we can start actual reading the datastore and secrets e.g. to read the datastore:
    content = api_read_datastores(token, session_secret_key)


    # 6. Read content of the first password datastore including all its shares, all secrets and filter the secrets
    datastore_content = None
    datastore_id = None
    datastore_secret = None
    for datastore in content['datastores']:
        if datastore['type'] != 'password':
            continue
        datastore_id = datastore['id']
        datastore_read_result = api_read_datastore(token, session_secret_key, datastore['id'])
        datastore_secret = decrypt_symmetric(datastore_read_result['secret_key'], datastore_read_result['secret_key_nonce'], user_secret_key)
        if 'data' in datastore_read_result and datastore_read_result['data']:
            datastore_content = json.loads(decrypt_symmetric(datastore_read_result['data'], datastore_read_result['data_nonce'], datastore_secret))
        else:
            datastore_content = {}
        break

    if datastore_id is None:
        print("No password datastore yet found, please create one for the user first with the webclient.")
        return

    # 7. reate a folder
    folder = create_folder_if_not_exist('My Folder', datastore_content)

    # 8. Create secret
    create_secret(
        token,
        session_secret_key,
        name='My Secret', # Thats the title shwon in the folder structure
        type='application_password', # The type of the entry.
        content={ # The actual content that will be stored on the external secret
            'application_password_title': 'My Secret',
            'application_password_username': 'MyUsername',
            'application_password_password': 'MyPassword',
            'application_password_notes': 'A note',
            'application_password_auto_submit': False,
            'application_password_url_filter': 'www.example.com',
        },
        folder=folder,
        datastore_id=datastore_id,
    )


    # 9. Encrypt Datastore
    encrypted_datastore = encrypt_symmetric(json.dumps(datastore_content), datastore_secret)

    # 10. Save new datastore content
    api_write_datastore(token, session_secret_key, datastore_id, encrypted_datastore['text'], encrypted_datastore['nonce'])

    # 11. Logout
    api_logout(token, session_secret_key)


if __name__ == '__main__':
    main()