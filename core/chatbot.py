import openai
import mysql.connector
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY

class SQLQueryView(View):
    template_name = 'chatbot.html'

    def get(self, request):
        # Render empty form on GET request
        return render(request, self.template_name)

    @csrf_exempt
    def post(self, request):
        # Handle the form submission
        query = request.POST.get('query')
        sql_command = self.generate_sql(query)
        result, error = self.execute_sql(sql_command)
        return JsonResponse({'sql': sql_command, 'result': result, 'error': error})

    def generate_sql(self, query):
        model_engine = "text-davinci-002"
        prompt = (
            "Given the following SQL tables, your job is to write queries given a user’s request."
            "CREATE TABLE auth_user ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   username VARCHAR(15),"
            "); "
            "CREATE TABLE core_userprofile ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   user_id INT,"
            "   address TEXT,"
            "   phone VARCHAR(15),"
            "   stripe_customer_id VARCHAR(50),"
            "   one_click_purchasing BOOLEAN DEFAULT FALSE,"
            "   rating_all DECIMAL(4, 1) DEFAULT 0,"
            "   rating_num INT DEFAULT 0"
            "); "
            "CREATE TABLE core_item ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   seller_id INT,"
            "   title VARCHAR(255),"
            "   description TEXT,"
            "   quantity INT,"
            "   starting_bid DECIMAL(9, 2),"
            "   condition VARCHAR(10),"
            "   system VARCHAR(10),"
            "   brand VARCHAR(50),"
            "   active BOOLEAN,"
            "   created_at DATETIME,"
            "   slug VARCHAR(255) UNIQUE,"
            "   image BLOB"
            "); "
            "CREATE TABLE core_orderitem ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   user_id INT,"
            "   ordered BOOLEAN DEFAULT FALSE,"
            "   item_id INT,"
            "   quantity INT,"
            "   price DECIMAL(9, 2)"
            "); "
            "CREATE TABLE core_bid ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   item_id INT,"
            "   bidder_id INT,"
            "   amount DECIMAL(9, 2),"
            "   time DATETIME DEFAULT CURRENT_TIMESTAMP"
            "); "
            "CREATE TABLE core_transaction ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   item_id INT,"
            "   buyer_id INT,"
            "   seller_id INT,"
            "   transaction_time DATETIME DEFAULT CURRENT_TIMESTAMP,"
            "   tracking_number VARCHAR(255)"
            "); "
            "CREATE TABLE core_order ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   user_id INT,"
            "   ref_code VARCHAR(20),"
            "   start_date DATETIME DEFAULT CURRENT_TIMESTAMP,"
            "   ordered_date DATETIME,"
            "   ordered BOOLEAN DEFAULT FALSE,"
            "   shipping_address_id INT,"
            "   billing_address_id INT,"
            "   payment_id INT,"
            "   coupon_id INT,"
            "   being_delivered BOOLEAN DEFAULT FALSE,"
            "   received BOOLEAN DEFAULT FALSE,"
            "   refund_requested BOOLEAN DEFAULT FALSE,"
            "   refund_granted BOOLEAN DEFAULT FALSE"
            "); "
            "CREATE TABLE core_address ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   user_id INT,"
            "   street_address VARCHAR(100),"
            "   apartment_address VARCHAR(100),"
            "   country VARCHAR(2),"
            "   zip VARCHAR(100),"
            "   address_type CHAR(1),"
            "   default BOOLEAN DEFAULT FALSE"
            "); "
            "CREATE TABLE core_payment ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   stripe_charge_id VARCHAR(50),"
            "   user_id INT,"
            "   amount FLOAT,"
            "   timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
            "); "
            "CREATE TABLE core_coupon ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   code VARCHAR(15),"
            "   amount FLOAT"
            "); "
            "CREATE TABLE core_refund ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   order_id INT,"
            "   reason TEXT,"
            "   accepted BOOLEAN DEFAULT FALSE,"
            "   email VARCHAR(255)"
            "); "
            "CREATE TABLE core_message ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   sender_id INT,"
            "   receiver_id INT,"
            "   item_id INT,"
            "   content TEXT,"
            "   sent_time DATETIME DEFAULT CURRENT_TIMESTAMP"
            "); "
            "CREATE TABLE core_rating ("
            "   id INT AUTO_INCREMENT PRIMARY KEY,"
            "   rated_by_id INT,"
            "   rated_user_id INT,"
            "   item_id INT,"
            "   rating TINYINT,"
            "   comment TEXT"
            "); "
            f"{query}\n"
            "SQL:"
        )

        response = openai.Completion.create(
            engine=model_engine,
            prompt=prompt,
            temperature=0,
            max_tokens=150,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=[";"]
        )
        return response.choices[0].text.strip()

    def execute_sql(self, sql_command):
        server_url = "35.233.133.184"
        db = "dev"
        user_name = "root"
        password = "y>AV_6fhBD?*RToL"

        try:
            connection = mysql.connector.connect(
                host=server_url,
                user=user_name,
                password=password,
                database=db
            )
            cursor = connection.cursor()
            cursor.execute(sql_command)
            result = cursor.fetchall()
            cursor.close()
            connection.close()
            return result, None
        except mysql.connector.Error as e:
            return None, str(e)
