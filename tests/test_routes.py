"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"

HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}

######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    ######################################################################
    #  G E T  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_get_account(self):
        """It should Read a single Account"""
        account = self._create_accounts(1)[0]
        resp = self.client.get(f"/accounts/{account.id}", content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], account.name)

    def test_get_account_not_found(self):
        """It should not Read an Account that is not found"""
        resp = self.client.get("/accounts/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    ######################################################################
    #  U P D A T E  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_update_account(self):
        """ It should update an account when valid data is provided."""
        # create an account
        test_account = self._create_accounts(1)[0]
        updated_account_data = {
            "name": "Updated Account Name", 
            "email": "updated.email@example.com", 
            "address": "123 Updated St", 
            "phone_number": "1234567890",
            "date_joined": "2022-12-31"
        }

        # update the account
        resp = self.client.put(
            f"{BASE_URL}/{test_account.id}",
            json=updated_account_data,
            content_type="application/json"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # check the updated account
        updated_account = resp.get_json()
        self.assertEqual(updated_account["name"], updated_account_data["name"])
        self.assertEqual(updated_account["email"], updated_account_data["email"])
        self.assertEqual(updated_account["address"], updated_account_data["address"])
        self.assertEqual(updated_account["phone_number"], updated_account_data["phone_number"])
        self.assertEqual(updated_account["date_joined"], updated_account_data["date_joined"])

    def test_update_account_not_found(self):
        """It should return 404_NOT_FOUND when updating a non-existing account"""
        fake_account = {"name": "Fake Account", "email": "fake@example.com", "address": "123 Fake St"}
        response = self.client.put("/accounts/0", json=fake_account, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_account_with_invalid_data(self):
        """It should reject the update when the account data is invalid"""
        account_data = {
            "name": "Test Account",
            "email": "test@example.com",
            "address": "Test Address"
        }

        # Create the account
        create_resp = self.client.post(
            "/accounts",
            json=account_data,
            content_type="application/json"
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        account_id = create_resp.json["id"]

        # Attempt to update the account with invalid data
        new_account = {"name": 1234, "email": "invalid"}

        update_resp = self.client.put(
            f"/accounts/{account_id}",
            json=new_account,
            content_type="application/json"
        )
        self.assertEqual(update_resp.status_code, status.HTTP_400_BAD_REQUEST)

    ######################################################################
    #  D E L E T E  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_delete_account(self):
        """It should delete an account"""
        # Create an account
        account_data = {
            "name": "Test Account",
            "email": "test@example.com",
            "address": "Test Address"
        }
        create_resp = self.client.post(
            "/accounts",
            json=account_data,
            content_type="application/json"
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        account_id = create_resp.json["id"]

        # Delete the account
        delete_resp = self.client.delete(f"/accounts/{account_id}")
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the account is deleted
        get_resp = self.client.get(f"/accounts/{account_id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_non_existing_account(self):
        """It should return 404_NOT_FOUND when deleting a non-existing account"""
        # Delete a non-existing account
        delete_resp = self.client.delete("/accounts/9999")
        self.assertEqual(delete_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_deleted_account(self):
        """It should return 404_NOT_FOUND when deleting an already deleted account"""
        # Create an account
        account_data = {
            "name": "Test Account",
            "email": "test@example.com",
            "address": "Test Address"
        }
        create_resp = self.client.post(
            "/accounts",
            json=account_data,
            content_type="application/json"
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        account_id = create_resp.json["id"]

        # Delete the account
        delete_resp = self.client.delete(f"/accounts/{account_id}")
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)

        # Try to delete the account again
        delete_resp_again = self.client.delete(f"/accounts/{account_id}")
        self.assertEqual(delete_resp_again.status_code, status.HTTP_404_NOT_FOUND)

    ######################################################################
    #  L I S T  A C C O U N T S   T E S T   C A S E S
    ######################################################################

    def test_list_accounts(self):
        """It should list all accounts"""
        # Create sample accounts
        account_data_1 = {"name": "Account 1", "email": "account1@example.com", "address": "Address 1"}
        account_data_2 = {"name": "Account 2", "email": "account2@example.com", "address": "Address 2"}

        self.client.post("/accounts", json=account_data_1, content_type="application/json")
        self.client.post("/accounts", json=account_data_2, content_type="application/json")

        # Retrieve the list of accounts
        response = self.client.get("/accounts")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the number of accounts in the response
        accounts = response.json
        self.assertEqual(len(accounts), 2)

        # Verify the account details
        account_1 = accounts[0]
        self.assertEqual(account_1["name"], account_data_1["name"])
        self.assertEqual(account_1["email"], account_data_1["email"])
        self.assertEqual(account_1["address"], account_data_1["address"])

        account_2 = accounts[1]
        self.assertEqual(account_2["name"], account_data_2["name"])
        self.assertEqual(account_2["email"], account_data_2["email"])
        self.assertEqual(account_2["address"], account_data_2["address"])
        
    ######################################################################
    #  O T H E R  T E S T   C A S E S
    ######################################################################

    def test_method_not_allowed(self):
        """It should not allow an illegal method call"""
        resp = self.client.delete(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ######################################################################
    #  T A L I S M A N  C O R S  T E S T   C A S E S
    ######################################################################

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)