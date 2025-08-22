from app import create_app
# A linha 'from manage import register_commands' não é mais necessária aqui.

app = create_app()
# A linha 'register_commands(app)' não é mais necessária aqui.

if __name__ == '__main__':
    app.run(debug=True)