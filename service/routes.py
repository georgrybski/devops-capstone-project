"""
Account Service

This microservice handles the lifecycle of Accounts
"""
# pylint: disable=unused-import
from flask import jsonify, request, make_response, abort, url_for   # noqa; F401
from service.models import Account, db
from service.common import status  # HTTP Status Codes
from . import app  # Import Flask application
import re
from datetime import date

############################################################
# Health Endpoint
############################################################
@app.route("/health")
def health():
    """Health Status"""
    return jsonify(dict(status="OK")), status.HTTP_200_OK


######################################################################
# GET INDEX
######################################################################
@app.route("/")
def index():
    """Root URL response"""
    return (
        jsonify(
            name="Account REST API Service",
            version="1.0",
            # paths=url_for("list_accounts", _external=True),
        ),
        status.HTTP_200_OK,
    )


######################################################################
# CREATE A NEW ACCOUNT
######################################################################
@app.route("/accounts", methods=["POST"])
def create_accounts():
    """
    Creates an Account
    This endpoint will create an Account based the data in the body that is posted
    """
    app.logger.info("Request to create an Account")
    check_content_type("application/json")
    account = Account()
    account.deserialize(request.get_json())
    account.create()
    message = account.serialize()
    # Uncomment once get_accounts has been implemented
    # location_url = url_for("get_accounts", account_id=account.id, _external=True)
    location_url = "/"  # Remove once get_accounts has been implemented
    return make_response(
        jsonify(message), status.HTTP_201_CREATED, {"Location": location_url}
    )

######################################################################
# LIST ALL ACCOUNTS
######################################################################

@app.route("/accounts", methods=["GET"])
def list_accounts():
    """
    List all Accounts
    This endpoint will return a list of all accounts
    """
    app.logger.info("Request to list all accounts")
    accounts = Account.query.all()
    serialized_accounts = [account.serialize() for account in accounts]
    return jsonify(serialized_accounts), status.HTTP_200_OK


######################################################################
# READ AN ACCOUNT
######################################################################

@app.route("/accounts/<int:account_id>", methods=["GET"])
def get_accounts(account_id):
    """
    Reads an Account
    This endpoint will read an Account based on the account_id that is requested
    """
    app.logger.info(f"Request to read an Account with id: {account_id}")
    account = Account.find(account_id)
    if not account:
        abort(status.HTTP_404_NOT_FOUND, f"Account with id [{account_id}] could not be found.")
    return account.serialize(), status.HTTP_200_OK


######################################################################
# UPDATE AN EXISTING ACCOUNT
######################################################################

@app.route("/accounts/<int:account_id>", methods=["PUT"])
def update_account(account_id):
    """
    Update an Account
    This endpoint will update an Account based on the body that is posted
    """
    app.logger.info("Request to update account with id: %s", account_id)
    account = Account.query.get(account_id)
    if not account:
        abort(status.HTTP_404_NOT_FOUND, "Account with id [{}] was not found.".format(account_id))

    account_data = request.get_json()

    if not validate_account_data(account_data):
        abort(status.HTTP_400_BAD_REQUEST, "Invalid account data provided.")

    account.deserialize(account_data)
    db.session.commit()

    return jsonify(account.serialize()), status.HTTP_200_OK

######################################################################
# DELETE AN ACCOUNT
######################################################################

@app.route("/accounts/<int:account_id>", methods=["DELETE"])
def delete_account(account_id):
    """
    Delete an Account
    This endpoint will delete an Account based on the provided account ID
    """
    app.logger.info("Request to delete account with id: %s", account_id)
    account = Account.query.get(account_id)
    if not account:
        abort(status.HTTP_404_NOT_FOUND, "Account with id [{}] was not found.".format(account_id))

    db.session.delete(account)
    db.session.commit()

    return "", status.HTTP_204_NO_CONTENT


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################


def check_content_type(media_type):
    """Checks that the media type is correct"""
    content_type = request.headers.get("Content-Type")
    if content_type and content_type == media_type:
        return
    app.logger.error("Invalid Content-Type: %s", content_type)
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {media_type}",
    )

def validate_account_data(account_data):
    """
    Validate the account data.
    Returns True if the data is valid, False otherwise.
    """
    if not isinstance(account_data.get("name"), str):
        return False
    if not isinstance(account_data.get("email"), str) or not validate_email(account_data["email"]):
        return False
    if not isinstance(account_data.get("address"), str):
        return False
    if "phone_number" in account_data and not isinstance(account_data["phone_number"], str):
        return False
    if "date_joined" in account_data:
        try:
            date.fromisoformat(account_data["date_joined"])
        except (TypeError, ValueError):
            return False
    return True

def validate_email(email):
    """
    Validate an email address using regular expressions.

    Returns True if the email address is valid, False otherwise.
    """
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None