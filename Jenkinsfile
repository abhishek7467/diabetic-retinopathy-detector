pipeline {
    agent any

    environment {
        VENV_DIR = 'venv'
    }

    stages {
        stage('Clone Repo') {
            steps {
                echo 'Cloning Git repository...'
                // Jenkins will automatically clone the repo if this Jenkinsfile is from SCM
                // No need to explicitly call `git` unless you want to override
            }
        }

        stage('Set up Python Virtual Environment') {
            steps {
                echo 'Creating virtual environment and installing dependencies...'
                sh '''
                    python3 -m venv $VENV_DIR
                    source $VENV_DIR/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Flask App') {
            steps {
                echo 'Running Flask app...'
                sh '''
                    source $VENV_DIR/bin/activate
                    nohup gunicorn -b 0.0.0.0:5000 app:app &
                '''
            }
        }
    }

    post {
        failure {
            echo 'Build failed. Please check the logs.'
        }
    }
}
