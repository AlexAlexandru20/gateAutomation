import subprocess
import os

def installDependencies():
    try:
        dependencies = ['pytz', 'fpdf2', 'validate-email-address', 'flask', 'flask-login', 'flask-mail', 'flask-oauthlib', 'flask-sqlalchemy', 'Flask-SSE', 'qrcode', 'pandas', 'opencv-python', 'numpy', 'pyzbar', 'flask-socketio', 'flask-cors', 'Pillow']
        for dependency in dependencies:
            print(f'Installing {dependency}')
            subprocess.check_call(['pip', 'install', dependency])

        print('Install successfully')

        run_exe()
    except subprocess.CalledProcessError as e:
        print(f'Instalation error: {e}')
    except Exception as e:
        print(f'Error: {e}')


def run_exe():
    try:
        print('Running .exe file: ')
        subprocess.check_call([os.path.join('EXE File', 'vcredist_x64.exe')])
    except subprocess.CalledProcessError as e:
        print(f'Error while installing: {e}')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    installDependencies()