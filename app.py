
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from api.transaction.endpoints import transactions_endpoints
from flasgger import Swagger

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)

CORS(app)
Swagger(app)


# register the blueprint
app.register_blueprint(transactions_endpoints, url_prefix='/api/transactions')


if __name__ == '__main__':
    app.run(debug=True)

