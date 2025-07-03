pipeline {
    agent any

    triggers {
        githubPush() // webhook-based trigger
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    credentialsId: '4041c808-ea64-46ed-bd5f-7f5f8109efb5',
                    url: 'https://github.com/abhishek7467/diabetic-retinopathy-detector.git'
            }
        }

        stage('Setup') {
            steps {
                sh '''
                python3 -m venv venv
                . venv/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Run Flask App') {
            steps {
                sh '''
                . venv/bin/activate
                nohup python run.py > app.log 2>&1 &
                '''
            }
        }
    }
}
