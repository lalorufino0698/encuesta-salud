"""Prueba LDAPS de solo lectura; no guarda credenciales ni modifica AD."""
import argparse
import getpass
import socket
import ssl
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='DC02.cafedcallao.gob.pe')
    parser.add_argument('--port', type=int, default=636)
    parser.add_argument('--ca-file', help='Certificado PEM de la CA, si no esta en Windows')
    parser.add_argument('--check-only', action='store_true', help='Solo comprobar TLS, sin credenciales')
    args = parser.parse_args()
    try:
        context = ssl.create_default_context(cafile=args.ca_file)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        with socket.create_connection((args.host, args.port), timeout=10) as raw:
            with context.wrap_socket(raw, server_hostname=args.host) as secure:
                print(f'OK: conexion {secure.version()}, certificado y nombre validados.')
    except ssl.SSLCertVerificationError as exc:
        print(f'ERROR de certificado: {exc.verify_message}')
        print('Verifica el certificado de DC02 y la confianza en su CA. Puedes usar --ca-file ruta.pem.')
        return 1
    except (OSError, ValueError) as exc:
        print(f'ERROR de conexion TLS: {exc}')
        return 1
    if args.check_only:
        return 0
    try:
        from ldap3 import BASE, SIMPLE, Connection, Server, Tls
        from ldap3.core.exceptions import LDAPException
    except ImportError:
        print('Instala las dependencias: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.ad.txt')
        return 1
    if not sys.stdin.isatty():
        print('Ejecuta esta prueba en tu terminal para introducir las credenciales de forma privada.')
        return 1
    username = input('Usuario UPN (usuario@cafedcallao.gob.pe): ').strip()
    password = getpass.getpass('Contrasena (no se muestra ni se guarda): ')
    if not username or not password:
        print('ERROR: usuario y contrasena no pueden estar vacios.')
        return 1
    tls = Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=args.ca_file,
              version=ssl.PROTOCOL_TLS_CLIENT)
    server = Server(args.host, port=args.port, use_ssl=True, tls=tls,
                    connect_timeout=10, get_info='NO_INFO')
    conn = Connection(server, user=username, password=password, authentication=SIMPLE,
                      read_only=True, auto_referrals=False, receive_timeout=10)
    try:
        if not conn.bind():
            print('ERROR de autenticacion:', conn.result.get('description'))
            print('Revisa la cuenta y las politicas de AD; no se reintentara automaticamente.')
            return 2
        print('OK: autenticacion aceptada por Active Directory.')
        if not conn.search('', '(objectClass=*)', search_scope=BASE,
                           attributes=['defaultNamingContext', 'dnsHostName']):
            print('ERROR de lectura RootDSE:', conn.result.get('description'))
            return 3
        if not conn.entries:
            print('ERROR: el servidor no devolvio RootDSE.')
            return 3
        entry = conn.entries[0]
        base = entry['defaultNamingContext'].value
        print('Controlador:', entry['dnsHostName'].value)
        print('Base DN:', base)
        if not base or not conn.search(base, '(objectClass=*)', search_scope=BASE,
                                        attributes=['distinguishedName']):
            print('ERROR: no se pudo leer la base del dominio.')
            return 3
        print('OK: consulta de lectura del dominio completada. No se modificaron objetos.')
        return 0
    except (LDAPException, OSError) as exc:
        print('ERROR LDAP:', type(exc).__name__)
        return 4
    finally:
        conn.unbind()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nPrueba cancelada.')
        sys.exit(130)
