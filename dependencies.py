import subprocess
import os

run_exe()

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
