from flask import Flask, redirect, render_template, jsonify, request, url_for, session, flash, Response
import sqlite3
import pickle
import tensorflow as tf
from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences
from pyvi import ViTokenizer
from werkzeug.security import generate_password_hash, check_password_hash

import google.generativeai as genai
import csv
import io

app = Flask(__name__)
app.secret_key = '__xoai__'

# Load model and tokenizer
my_model = load_model('model_cnn.keras')
with open('tokenizer_data.pkl', 'rb') as file:
    my_tokenizer = pickle.load(file)

# Configure Google Generative AI API key
genai.configure(api_key="AIzaSyCpISZmPOZs_QL4KrQlyHHaZm4d2cKhMPU")

# Set up the Google Generative AI model configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Function to connect to the database
def get_db_connection():
    conn = sqlite3.connect('db/csdl.db')
    conn.row_factory = sqlite3.Row
    return conn

# Function to preprocess input text using the tokenizer
def preprocess_raw_input(raw_input, tokenizer):
    input_text_pre = list(tf.keras.preprocessing.text.text_to_word_sequence(raw_input))
    input_text_pre = " ".join(input_text_pre)
    input_text_pre_accent = ViTokenizer.tokenize(input_text_pre)
    tokenizer_data_text = tokenizer.texts_to_sequences([input_text_pre_accent])
    vec_data = pad_sequences(tokenizer_data_text, padding='post', maxlen=820)
    return vec_data

# Function to make predictions using the model
def inference_model(input_feature, model):
    output = model(input_feature).numpy()[0]
    result = output.argmax()
    label_dict = {0: 'Tiêu cực', 1: 'Trung lập', 2: 'Tích cực'}
    return label_dict[result]

def update_sentimentai(id, sentiment_ai):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE reviews 
        SET sentiment_ai = ? 
        WHERE id = ?
    """, (sentiment_ai, id))
    conn.commit()
    conn.close()

@app.route('/dangki', methods=['GET', 'POST'])
def dangki():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Mật khẩu và xác nhận mật khẩu không khớp.")
            return redirect(url_for('dangki'))

        conn = get_db_connection()
        # Check if the email already exists
        existing_user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        
        if existing_user:
            flash("Email đã tồn tại. Vui lòng sử dụng email khác.")
            return redirect(url_for('dangki'))

        # Hash the password using pbkdf2:sha256
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                     (name, email, hashed_password))
        conn.commit()
        conn.close()

        flash("Đăng ký thành công! Bạn có thể đăng nhập ngay.")
        return redirect(url_for('dangnhap'))

    return render_template('user/dangki.html')


@app.route('/logout')  # Route để đăng xuất
def logout():
    session.pop('user_id', None)  # Xóa thông tin người dùng khỏi session
    session.pop('email', None)
    flash('Đăng xuất thành công!', 'success')
    return redirect(url_for('trangchu'))  # Chuyển hướng về trang chính hoặc trang đăng nhập

@app.route('/dangnhap', methods=['GET', 'POST'])
def dangnhap():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):  # Kiểm tra mật khẩu đã mã hóa
            session['user_id'] = user['user_id']  # Lưu user_id vào session
            session['email'] = user['email']
            session['username'] = user['username']  # Giả sử bạn đã lưu tên người dùng
            flash("Đăng nhập thành công!")
            return redirect(url_for('trangchu'))  # Chuyển tới trang chính sau khi đăng nhập
        else:
            flash("Email hoặc mật khẩu không chính xác.")
            return redirect(url_for('dangnhap'))

    return render_template('user/dangnhap.html')


@app.route('/')
def trangchu():
     conn = get_db_connection()

     # Truy vấn các sản phẩm thuộc danh mục có category_id = 1 (điện thoại di động)
     featured_di_dong = conn.execute("SELECT * FROM products WHERE category_id = 1 ORDER BY total_sold DESC LIMIT 3").fetchall()

     # Truy vấn sản phẩm mới nhất từ bảng products có biến thể
     products_query = """
     SELECT p.product_id, p.name, p.image_url, v.color, v.storage, v.price
     FROM products p
     LEFT JOIN product_variants v ON p.product_id = v.product_id
     ORDER BY p.created_at DESC
     LIMIT 12
     """
     products_raw = conn.execute(products_query).fetchall()

     products = []
     product_map = {}

     for row in products_raw:
         product_id = row['product_id']
        
         # Nếu sản phẩm chưa tồn tại trong danh sách, tạo mới
         if product_id not in product_map:
             product = {
                'product_id': product_id,
                 'name': row['name'],
                 'image_url': row['image_url'],
                 'colors': [],
                 'storage_options': [],
                'price_options': []
             }
             product_map[product_id] = product
             products.append(product)  # Thêm sản phẩm vào danh sách products
        
         # Cập nhật màu sắc nếu có
         if row['color'] and row['color'] not in product_map[product_id]['colors']:
             product_map[product_id]['colors'].append(row['color'])
        
         # Cập nhật dung lượng và giá nếu có
         if row['storage'] and row['price']:
             if row['storage'] not in product_map[product_id]['storage_options']:
                 product_map[product_id]['storage_options'].append(row['storage'])
             if row['price'] not in product_map[product_id]['price_options']:
                 product_map[product_id]['price_options'].append(row['price'])

     conn.close()

     # Trả về kết quả và render trang chủ, truyền thêm hàm zip vào
     return render_template(
         'user/trangchu.html', 
         featured_di_dong=featured_di_dong,
         products=products,
         zip=zip  # Truyền hàm zip vào template
     )


@app.route('/categories/<int:category_id>')  # Nhận category_id là số nguyên
def sanpham(category_id):
    # Kết nối đến cơ sở dữ liệu
    conn = get_db_connection()

    # Truy vấn sản phẩm theo category_id
    goiy_di_dong = conn.execute(
        "SELECT * FROM products WHERE category_id = ? ORDER BY total_stock DESC LIMIT 4", 
        (category_id,)
    ).fetchall()

    # Truy vấn sản phẩm mới nhất từ bảng products có biến thể và tính điểm trung bình và số lượng đánh giá
    products_query = """
    SELECT p.product_id, p.name, p.image_url, v.color, v.storage, v.price,
        r.rating,
        COALESCE(COUNT(r.rating), 0) AS review_count
    FROM products p
    LEFT JOIN product_variants v ON p.product_id = v.product_id
    LEFT JOIN reviews r ON p.product_id = r.product_id  -- Giả sử bạn có bảng reviews
    WHERE p.category_id = ?
    GROUP BY p.product_id, v.color, v.storage, v.price
    ORDER BY p.created_at DESC
    LIMIT 15
    """

    products_raw = conn.execute(products_query, (category_id,)).fetchall()

    products = []
    product_map = {}

    # Danh sách để lưu trạng thái has_purchased cho từng sản phẩm
    product_purchase_status = {}

    for row in products_raw:
        product_id = row['product_id']
        
        # Nếu sản phẩm chưa tồn tại trong danh sách, tạo mới
        if product_id not in product_map:
            product = {
                'product_id': product_id,
                'name': row['name'],
                'image_url': row['image_url'],
                'colors': [],
                'storage_options': [],
                'price_options': [],
                'review_count': row['review_count']       # Số lượng đánh giá
            }
            product_map[product_id] = product
            products.append(product)  # Thêm sản phẩm vào danh sách products
        
        # Cập nhật màu sắc nếu có
        if row['color'] and row['color'] not in product_map[product_id]['colors']:
            product_map[product_id]['colors'].append(row['color'])
        
        # Cập nhật dung lượng và giá nếu có
        if row['storage'] and row['price']:
            if row['storage'] not in product_map[product_id]['storage_options']:
                product_map[product_id]['storage_options'].append(row['storage'])
            if row['price'] not in product_map[product_id]['price_options']:
                product_map[product_id]['price_options'].append(row['price'])

    for product in products:
            product_id = product['product_id']

            # Lấy tất cả các đánh giá của sản phẩm
            ratings_query = """
            SELECT rating FROM reviews WHERE product_id = ?
            """
            ratings_raw = conn.execute(ratings_query, (product_id,)).fetchall()

            if ratings_raw:
                # Tính tổng điểm và số lượng đánh giá
                total_rating = sum([rating['rating'] for rating in ratings_raw])
                review_count = len(ratings_raw)
                average_rating = round(total_rating / review_count, 1)  # Tính trung bình và làm tròn
                product['average_rating'] = average_rating
    # Lấy danh sách các thương hiệu
    brands = conn.execute("SELECT * FROM brands").fetchall()  # Giả sử bạn có bảng brands
    
    # Lấy user_id từ session
    user_id = session.get('user_id')

    # Nếu không có user_id, gán giá trị mặc định là None
    if user_id is None:
        user_id = None  # Gán giá trị None cho user_id nếu không tìm thấy

    # Kiểm tra trạng thái has_purchased cho từng sản phẩm
    for product in products:
        product_id = product['product_id']

        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN o.order_status_id IN ('4', '6') THEN 1 ELSE 0 END) AS count_4_5_6
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN product_variants pv ON pv.variant_id = oi.product_variant_id
            WHERE pv.product_id = ? 
            AND o.user_id = ?
            GROUP BY pv.product_id
        ''', (product_id, user_id))

        result = cursor.fetchone()  # Lấy kết quả đầu tiên

        # Kiểm tra nếu có ít nhất một đơn hàng
        has_purchased = result is not None and result[0] > 0  # Có ít nhất một đơn hàng với status 4, 6

        # Lưu trạng thái has_purchased cho sản phẩm
        product_purchase_status[product_id] = has_purchased

    # Đóng kết nối
    conn.close()
    

    # Trả về template với các biến cần thiết
    return render_template(
        'user/sanpham.html', 
        products=products, 
        brands=brands, 
        zip=zip,
        goiy_di_dong=goiy_di_dong,
        product_purchase_status=product_purchase_status  # Gửi trạng thái has_purchased cho template
    )



def get_product_details(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()

    if product:
        return {
            'product_id': product['product_id'],
            'name': product['name'],
            'description': product['description'],
            'price': product['price'],
            'brand': product['brand_id'],
            'category_id': product['category_id'],
            'stock': product['total_stock'],
            'image_url': product['image_url'],
            'created_at': product['created_at']
            
        }
    else:
        return None
@app.route('/product/<int:product_id>', methods=['GET'])
def show_product_and_reviews(product_id):  # Accept user_id as an argument
    conn = get_db_connection()
    user_id = session.get('user_id')

    # Truy vấn biến thể sản phẩm (dung lượng, màu sắc, giá)
    product_query = """
    SELECT p.product_id, p.name, p.image_url, v.color, v.storage, v.price, p.average_rating, p.review_count, p.negative_summary, p.positive_summary
    FROM products p
    LEFT JOIN product_variants v ON p.product_id = v.product_id
    WHERE p.product_id = ?
    """
    product_variants = conn.execute(product_query, (product_id,)).fetchall()

    # Tạo một dict để lưu các biến thể của sản phẩm
    product_map = {}

    if product_variants:
        all_colors_set = set()
        for row in product_variants:
            prod_id = row['product_id']
            if prod_id not in product_map:
                product = {
                    'product_id': prod_id,
                    'name': row['name'],
                    'average_rating': row['average_rating'],
                    'review_count': row['review_count'],
                    'image_url': row['image_url'],
                    'colors': {},
                    'storage_options': [],
                    'price_options': [],
                    'all_colors': set(),
                    'negative_summary': row['negative_summary'],
                    'positive_summary' : row['positive_summary']
                }
                product_map[prod_id] = product
            
            if row['color']:
                all_colors_set.add(row['color'])
                if row['storage'] not in product_map[prod_id]['colors']:
                    product_map[prod_id]['colors'][row['storage']] = set()
                product_map[prod_id]['colors'][row['storage']].add(row['color'])

            if row['storage'] not in product_map[prod_id]['storage_options']:
                product_map[prod_id]['storage_options'].append(row['storage'])
                product_map[prod_id]['price_options'].append(row['price'])

    for prod in product_map.values():
        prod['all_colors'] = list(all_colors_set)
        for storage in prod['colors']:
            prod['colors'][storage] = list(prod['colors'][storage])
    
    product_details = get_product_details(product_id)
    product = product_map.get(product_id, {})
    if product_details:
        product.update(product_details)

    # Kiểm tra xem người dùng đã mua sản phẩm chưa
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            o.order_id,
            SUM(CASE WHEN o.order_status_id IN ('4', '6') THEN 1 ELSE 0 END) AS count_4_5_6,
            SUM(CASE WHEN o.order_status_id = '4' THEN 1 ELSE 0 END) AS count_4,
            SUM(CASE WHEN o.order_status_id = '6' THEN 1 ELSE 0 END) AS count_6
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN product_variants pv ON pv.variant_id = oi.product_variant_id
        WHERE pv.product_id = ? 
        AND o.user_id = ?
        GROUP BY o.order_id
    ''', (product_id, user_id))

    results = cursor.fetchall()  # Lấy tất cả các hàng kết quả

    order_ids = []  # Danh sách để lưu trữ tất cả order_id
    total_count_4_5_6 = 0  # Tổng số đơn hàng có trạng thái 4, 5 hoặc 6
    total_count_4 = 0
    total_count_6 = 0

    for result in results:
        order_ids.append(result[0])  # Thêm order_id vào danh sách
        total_count_4_5_6 += result[1]  # Cộng dồn số lượng cho trạng thái 4, 5, 6
        total_count_4 += result[2]
        total_count_6 += result[3]

    # Kiểm tra nếu có ít nhất một đơn hàng
    has_purchased = total_count_4_5_6 > 0  # Có ít nhất một đơn hàng với status 4, 5 hoặc 6
    has_purchased_4 = total_count_4 > 0
    has_purchased_6 = total_count_6 > 0
    # Lấy order_id đầu tiên nếu có
    order_id = max(order_ids) if order_ids else None

    sentiment_filter = request.args.get('sentiment_filter')  # Lấy tham số lọc cảm xúc từ URL

    # Truy vấn đánh giá của sản phẩm
    cursor.execute("SELECT * FROM reviews WHERE product_id = ? ORDER BY created_at DESC", (product_id,))
    reviews = cursor.fetchall()
    conn.close()

    filtered_reviews = [
        review for review in reviews
        if not sentiment_filter or review['sentiment_ai'] == sentiment_filter
    ]

    review_data = []
    sentiment_counts = {'Tích cực': 0, 'Trung lập': 0, 'Tiêu cực': 0}
    ratings = []
    rating_counts = {i: 0 for i in range(1, 6)}

    for review in reviews:
        comment = review['comment']
        if review['sentiment_ai'] is None:
            input_model = preprocess_raw_input(comment, my_tokenizer)
            sentiment_ai = inference_model(input_model, my_model)
            update_sentimentai(review['id'], sentiment_ai)
        else:
            sentiment_ai = review['sentiment_ai']

        sentiment_counts[sentiment_ai] += 1
        review_data.append({
            'id': review['id'],
            'product_id': review['product_id'],
            'user_id': review['user_id'],
            'variant_id': review['product_variant_id'],
            'rating': review['rating'],
            'comment': review['comment'],
            'sentiment': review['sentiment'],
            'sentiment_ai': sentiment_ai,
            'review_date': review['created_at']
        })

        rating = int(review['rating'])
        ratings.append(rating)
        rating_counts[rating] += 1
        average_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
        product['average_rating'] = average_rating


    # Render ra template, thêm biến has_purchased vào context
    return render_template('user/spchitiet.html', product=product, reviews=review_data, has_purchased_4=has_purchased_4, has_purchased_6=has_purchased_6,
                           sentiment_counts=sentiment_counts,
                           rating_counts=rating_counts, zip=zip,
                           has_purchased=has_purchased,order_id=order_id, filtered_reviews=filtered_reviews)  # Truyền thông tin đã mua đến template


@app.route('/cart')
def show_cart():
    user_id = session.get('user_id')  # Lấy user_id từ session
    if not user_id:  # Kiểm tra nếu chưa đăng nhập
        flash("Bạn cần đăng nhập để xem giỏ hàng.", "warning")
        return redirect(url_for('dangnhap'))

    conn = get_db_connection()
    try:
        # Truy vấn giỏ hàng của người dùng từ bảng carts
        cart_items = conn.execute('''
            SELECT c.cart_id, pv.product_id, p.name, pv.storage, pv.color, c.quantity, c.price, c.product_variant_id
            FROM carts c
            JOIN product_variants pv ON c.product_variant_id = pv.variant_id
            JOIN products p ON pv.product_id = p.product_id
            WHERE c.user_id = ?
        ''', (user_id,)).fetchall()

        # Kiểm tra nếu giỏ hàng không rỗng
        if cart_items:
            # Tính tổng giá trị giỏ hàng
            total_price = round(sum(item['quantity'] * item['price'] for item in cart_items), 2)
            total_quantity = sum(item['quantity'] for item in cart_items)
        else:
            flash("Giỏ hàng trống.", 'info')
            total_price = 0
            total_quantity = 0

    except Exception as e:
        return str(e), 500  # Trả về lỗi nếu có bất kỳ vấn đề nào xảy ra

    finally:
        conn.close()

    # Render template giỏ hàng và truyền dữ liệu
    return render_template('user/giohang.html', cart_items=cart_items, total_price=total_price, total_quantity=total_quantity)

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    user_id = session.get('user_id')
    print(user_id)

    if not user_id:
        # Trả về phản hồi JSON thay vì redirect
        return jsonify(success=False, redirect=url_for('dangnhap'), message="Bạn cần đăng nhập để mua hàng."), 401
    data = request.get_json()

    # Lấy thông tin từ yêu cầu POST
    product_id = data['product_id']
    storage = data['storage']
    color = data['color']
    quantity = int(data['quantity'])
    price = float(data['price'])
    
    conn = get_db_connection()
    
    # Lấy variant_id dựa trên product_id, storage và color
    product_variant = conn.execute('''
        SELECT variant_id FROM product_variants
        WHERE product_id = ? AND storage = ? AND color = ?
    ''', (product_id, storage, color)).fetchone()

    if not product_variant:
        conn.close()
        return jsonify(success=False, error="Không tìm thấy biến thể sản phẩm."), 404

    product_variant_id = product_variant['variant_id']

    # Kiểm tra nếu sản phẩm đã tồn tại trong giỏ hàng
    existing_item = conn.execute('''
        SELECT * FROM carts
        WHERE user_id = ? AND product_variant_id = ?
    ''', (user_id, product_variant_id)).fetchone()

    if existing_item:
        # Cập nhật số lượng nếu sản phẩm đã có trong giỏ hàng
        new_quantity = existing_item['quantity'] + quantity
        conn.execute('UPDATE carts SET quantity = ? WHERE cart_id = ?', (new_quantity, existing_item['cart_id']))
    else:
        # Thêm sản phẩm mới vào giỏ hàng
        conn.execute('''
            INSERT INTO carts (user_id, product_variant_id, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', (user_id, product_variant_id, quantity, price))
    
    conn.commit()
    conn.close()

    return jsonify(success=True)


@app.route('/delete-cart-item', methods=['POST'])
def delete_cart_item():
    user_id = session.get('user_id')  # Lấy user_id từ session
    if not user_id:
        flash("Bạn cần đăng nhập để xóa sản phẩm khỏi giỏ hàng.", "warning")
        return redirect(url_for('login'))  # Chuyển hướng nếu chưa đăng nhập
    
    product_variant_id = request.form['product_variant_id']

    conn = get_db_connection()

    # Xóa sản phẩm khỏi giỏ hàng
    conn.execute('DELETE FROM carts WHERE user_id = ? AND product_variant_id = ?', 
                 (user_id, product_variant_id))
    conn.commit()
    conn.close()

    flash("Sản phẩm đã được xóa khỏi giỏ hàng.", "success")
    return redirect(url_for('show_cart'))

@app.route('/update-cart', methods=['POST'])
def updatecart():
    user_id = session.get('user_id')  # Lấy user_id từ session
    if not user_id:
        flash("Bạn cần đăng nhập để xóa sản phẩm khỏi giỏ hàng.", "warning")
        return redirect(url_for('login'))  # Chuyển hướng nếu chưa đăng nhập
    
    product_variant_id = request.form['product_variant_id']
    quantity = request.form['quantity']  # Get the updated quantity

    conn = get_db_connection()

    # Xóa sản phẩm khỏi giỏ hàng
    conn.execute('UPDATE carts SET quantity = ? WHERE user_id = ? AND product_variant_id = ?',
                 (quantity, user_id, product_variant_id))
    conn.commit()
    conn.close()

    return redirect(url_for('show_cart'))

@app.route('/dathangtt', methods=['GET', 'POST'])
def checkoutm():
    # Kiểm tra người dùng đã đăng nhập hay chưa
    user_id = session.get('user_id')
    if not user_id:
        flash("Bạn cần đăng nhập để mua hàng.", "warning")
        return jsonify(success=False, redirect=url_for('dangnhap'))  # Chuyển hướng đến đăng nhập nếu chưa đăng nhập

    # Kết nối đến cơ sở dữ liệu
    conn = get_db_connection()

    if request.method == 'GET':
        # Lấy các tham số từ URL
        product_id = request.args.get('product_id')
        storage = request.args.get('storage')
        color = request.args.get('color')
        quantity = request.args.get('quantity')
        price = request.args.get('price')

        # Kiểm tra các tham số có hợp lệ không
        if not all([product_id, storage, color, quantity, price]):
            return jsonify(success=False, error="Thiếu thông tin sản phẩm hoặc thông tin không hợp lệ."), 400

        try:
            quantity = int(quantity)
            price = float(price)
        except ValueError:
            return jsonify(success=False, error="Số lượng hoặc giá không hợp lệ."), 400

        # Truy vấn database để lấy variant_id
        product_variant = conn.execute('''
            SELECT variant_id FROM product_variants
            WHERE product_id = ? AND storage = ? AND color = ?
        ''', (product_id, storage, color)).fetchone()

        if not product_variant:
            conn.close()
            return jsonify(success=False, error="Không tìm thấy biến thể sản phẩm."), 404

        product_variant_id = product_variant['variant_id']
        total_price = price * quantity

        # Tạo giỏ hàng
        cart_items = [{
            'product_id': product_id,
            'storage': storage,
            'color': color,
            'quantity': quantity,
            'price': price,
            'total_price': total_price
        }]
        
        total_quantity = quantity  # Tổng số lượng sản phẩm trong giỏ hàng

        conn.close()  # Đảm bảo đóng kết nối sau khi hoàn thành

        # Render template giỏ hàng
        return render_template('user/dathang.html', 
                               cart_items=cart_items, 
                               total_price=total_price, 
                               total_quantity=total_quantity)

    return render_template('user/dathang.html')  # Nếu là GET request ban đầu

@app.route('/dathang', methods=['GET'])
def checkout():
    # Lấy user_id từ session
    user_id = session.get('user_id')
    if not user_id:
        flash("Bạn cần đăng nhập để mua hàng.", "warning")  # Flash thông báo yêu cầu đăng nhập
        return redirect(url_for('dangnhap'))  # Chuyển hướng đến trang đăng nhập nếu chưa đăng nhập

    # Kết nối đến cơ sở dữ liệu
    conn = get_db_connection()

    try:
        # Lấy các mặt hàng trong giỏ hàng của người dùng
        cart_items = conn.execute('''
            SELECT c.cart_id, pv.product_id, p.name, pv.storage, pv.color, c.quantity, c.price, c.product_variant_id
            FROM carts c
            JOIN product_variants pv ON c.product_variant_id = pv.variant_id
            JOIN products p ON pv.product_id = p.product_id
            WHERE c.user_id = ?
        ''', (user_id,)).fetchall()

        # Kiểm tra nếu giỏ hàng không trống
        if cart_items:
            # Tính tổng giá trị và số lượng giỏ hàng
            total_price = round(sum(item['quantity'] * item['price'] for item in cart_items), 2)
            total_quantity = sum(item['quantity'] for item in cart_items)

            # Render trang thanh toán
            return render_template('user/dathang.html', 
                                   cart_items=cart_items, 
                                   total_price=total_price, 
                                   total_quantity=total_quantity)
        else:
            flash('Không có sản phẩm nào trong giỏ hàng!', 'info')  # Flash thông báo giỏ hàng trống
            return redirect(url_for('show_cart'))  # Chuyển hướng đến trang giỏ hàng

    finally:
        # Đóng kết nối sau khi truy vấn xong
        conn.close()

    
@app.route('/guidathang', methods=['POST'])
def submit_order():
    user_id = session.get('user_id')  # Lấy user_id từ session hoặc bất kỳ cơ chế nào bạn sử dụng để xác định người dùng
    # Lấy thông tin từ form
    name = request.form.get('name')
    phone_number = request.form.get('number')
    address = f"{request.form.get('dinoselect')} - {request.form.get('dinoselect2')} - {request.form.get('dinoselect3')} - {request.form.get('address')}"
    message = request.form.get('message')  # Ghi chú của khách hàng
    payment_method = request.form.get('dinoselect5')  # Phương thức thanh toán

    # Lấy user_id từ session hoặc phương thức xác thực khác (ở đây dùng tạm user_id là 1)
   

    conn = get_db_connection()

    # Truy vấn các mặt hàng trong giỏ hàng của người dùng
    cart_items = conn.execute('''
            SELECT c.cart_id, pv.product_id, p.name, pv.storage, pv.color, c.quantity, c.price, c.product_variant_id
            FROM carts c
            JOIN product_variants pv ON c.product_variant_id = pv.variant_id
            JOIN products p ON pv.product_id = p.product_id
            WHERE c.user_id = ?
        ''', (user_id,)).fetchall()

    # Tính tổng giá trị đơn hàng
    total_price = round(sum(item['quantity'] * item['price'] for item in cart_items), 2)

    # Thêm đơn hàng vào bảng orders
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (user_id, customer_name, phone_number, delivery_address, total_amount, order_status_id, payment_method, customer_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, phone_number, address, total_price, 1, payment_method, message))  # Thay 'Pending' bằng ID trạng thái là 1

    order_id = cursor.lastrowid  # Lấy ID của đơn hàng mới tạo

    # Thêm các mục trong giỏ hàng vào bảng order_items
    for cart_item in cart_items:
        cursor.execute('''
            INSERT INTO order_items (order_id, product_variant_id, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', (order_id, cart_item['product_variant_id'], cart_item['quantity'], cart_item['price']))

    # Xóa giỏ hàng của người dùng sau khi đặt hàng thành công
    cursor.execute('DELETE FROM carts WHERE user_id = ?', (user_id,))

    # Lưu thay đổi và đóng kết nối
    conn.commit()
    conn.close()

    # Sau khi hoàn thành đặt hàng, chuyển đến trang thành công và truyền order_id
    return render_template('user/thanhcong.html', id=order_id)


@app.route('/lichsudonhang/', defaults={'status_id': None}, methods=['GET'])
@app.route('/lichsudonhang/<int:status_id>', methods=['GET'])
def order_history(status_id):

    user_id = session.get('user_id')  # Lấy user_id từ session hoặc bất kỳ cơ chế nào bạn sử dụng để xác định người dùng
    conn = get_db_connection()  # Kết nối đến cơ sở dữ liệu

    # Truy vấn đơn hàng kèm theo trạng thái
    if status_id is None:
        orders = conn.execute('''
            SELECT o.*, s.status_name
            FROM orders o
            LEFT JOIN order_statuses s ON o.order_status_id = s.status_id
            WHERE o.user_id = ?
        ''', (user_id,)).fetchall()  # Lấy tất cả đơn hàng cho người dùng
    else:
        orders = conn.execute('''
            SELECT o.*, s.status_name
            FROM orders o
            LEFT JOIN order_statuses s ON o.order_status_id = s.status_id
            WHERE o.user_id = ? AND o.order_status_id = ?
        ''', (user_id, status_id)).fetchall()  # Lấy đơn hàng theo trạng thái cho người dùng

    
    # Truy vấn tất cả trạng thái đơn hàng để hiển thị trong template
    order_statuses = conn.execute('SELECT * FROM order_statuses LIMIT 5').fetchall()
    conn.close()  # Đóng kết nối
    
    return render_template('user/lsdh.html', orders=orders, statusid=status_id, order_statuses=order_statuses)

@app.route('/huydon/<int:order_id>/', methods=['POST'])
def cancel_order(order_id):
    conn = get_db_connection()
    conn.execute('''
        UPDATE orders
        SET order_status_id = (SELECT status_id FROM order_statuses WHERE status_name = 'Đã hủy')
        WHERE order_id = ?
    ''', (order_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('order_history'))  # Quay lại trang lịch sử đơn hàng

@app.route('/nhanhang/<int:order_id>/', methods=['POST'])
def confirm_order(order_id):
    conn = get_db_connection()
    conn.execute('''
        UPDATE orders
        SET order_status_id = (SELECT status_id FROM order_statuses WHERE status_name = 'Giao thành công')
        WHERE order_id = ?
    ''', (order_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('order_history'))  # Quay lại trang lịch sử đơn hàng

@app.route('/donhang/<int:order_id>/')
def order_details(order_id):
    user_id = session.get('user_id')  # Lấy user_id từ session hoặc bất kỳ cơ chế nào bạn sử dụng để xác định người dùng
    conn = get_db_connection()

    # Truy vấn thông tin chi tiết đơn hàng
    # Truy vấn để lấy thông tin từ bảng `orders`
    order = conn.execute('''
        SELECT o.*, s.status_name
        FROM orders o
        LEFT JOIN order_statuses s ON o.order_status_id = s.status_id
        WHERE o.order_id = ? AND o.user_id = ?
    ''', (order_id, user_id)).fetchone()

    # Truy vấn để lấy thông tin từ bảng `order_items`
    ordersi = conn.execute('''
        SELECT i.product_variant_id, pv.product_id, p.name, pv.storage, pv.color, i.quantity, i.price*i.quantity as total_price
        FROM order_items i
        JOIN product_variants pv ON i.product_variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        WHERE i.order_id = ?
    ''', (order_id,)).fetchall()
    conn.close()

    conn.close()

    # Kiểm tra xem đơn hàng có tồn tại không
    if order is None:
        return "Đơn hàng không tồn tại", 404

    return render_template('user/ctdonhang.html', ordersi=ordersi, order = order)

@app.route('/donhang/<int:order_id>/danhgia')
def review_order(order_id):
    conn = get_db_connection()
    # Lấy thông tin các sản phẩm trong đơn hàng
    order_items = conn.execute('''
        SELECT i.product_variant_id, pv.product_id, p.name, pv.storage, pv.color, i.quantity, i.price * i.quantity AS total_price
        FROM order_items i
        JOIN product_variants pv ON i.product_variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        WHERE i.order_id = ?
    ''', (order_id,)).fetchall()  # Sử dụng fetchall() để lấy tất cả các kết quả

    conn.close()

    # Kiểm tra nếu không có sản phẩm nào trong đơn hàng
    if not order_items:
        return "Đơn hàng không tồn tại hoặc không có sản phẩm nào", 404

    return render_template('user/danhgia.html', order_id=order_id, order_items=order_items)

@app.route('/donhang/<int:order_id>/danhgia/add', methods=['POST'])
def add_review(order_id):
    # Kết nối cơ sở dữ liệu
    conn = get_db_connection()
    user_id = session.get('user_id')

    for item in request.form:
        if item.startswith('sentiment_'):
            product_variant_id = item.split('_')[1]
            sentiment = request.form[item]
            rating = request.form.get(f'rating_{product_variant_id}')
            review = request.form.get(f'review_{product_variant_id}')

            # Lấy product_id từ product_variant_id
            product_id_query = conn.execute('SELECT product_id FROM product_variants WHERE variant_id = ?', (product_variant_id,))
            product_id = product_id_query.fetchone()

            if product_id:
                order_item_query = conn.execute('SELECT order_item_id FROM order_items WHERE order_id = ? AND product_variant_id = ?', (order_id, product_variant_id))
                order_item = order_item_query.fetchone()
                
                if order_item:
                    order_item_id = order_item[0]

                    input_model = preprocess_raw_input(review, my_tokenizer)
                    sentiment_ai = inference_model(input_model, my_model)

                    conn.execute('''
                        INSERT INTO reviews (product_variant_id, product_id, user_id, sentiment, rating, comment, sentiment_ai, order_item_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (product_variant_id, product_id[0], user_id, sentiment, rating, review, sentiment_ai, order_item_id))

                    # Cập nhật trạng thái đơn hàng sau khi có đánh giá
                    conn.execute('UPDATE orders SET order_status_id = 6 WHERE order_id = ?', (order_id,))
                    conn.commit()
                    # Tóm tắt lại tất cả các đánh giá (mới và cũ)
                    summarize_and_update_reviews(product_id[0], conn)

    conn.commit()
    conn.close()
    return render_template('user/danhgiathanhcong.html', order_id=order_id)


@app.route('/donhang/<int:order_id>/danhgia/update', methods=['POST'])
def update_review(order_id):
    conn = get_db_connection()
    user_id = session.get('user_id')

    order_items = conn.execute('''
        SELECT order_item_id, product_variant_id
        FROM order_items
        WHERE order_id = ? 
    ''', (order_id,)).fetchall()

    for item in order_items:
        product_variant_id = item['product_variant_id']
        order_item_id = item['order_item_id']
        
        sentiment = request.form.get(f'sentiment_{product_variant_id}')
        rating = request.form.get(f'rating_{product_variant_id}')
        review = request.form.get(f'review_{product_variant_id}')
        
        review_data = conn.execute('''
            SELECT id 
            FROM reviews 
            WHERE user_id = ? AND product_variant_id = ? AND order_item_id = ?
        ''', (user_id, product_variant_id, order_item_id)).fetchone()

        if review_data:
            review_id = review_data['id']
            
            if review:
                input_model = preprocess_raw_input(review, my_tokenizer)
                sentiment_ai = inference_model(input_model, my_model)

                if sentiment and rating:
                    conn.execute('''
                        UPDATE reviews 
                        SET sentiment = ?, rating = ?, comment = ?, sentiment_ai = ?
                        WHERE id = ?
                    ''', (sentiment, rating, review, sentiment_ai, review_id))

                    product_id_query = conn.execute('SELECT product_id FROM product_variants WHERE variant_id = ?', (product_variant_id,))
                    conn.commit()
                    product_id = product_id_query.fetchone()
                    if product_id:
                        summarize_and_update_reviews(product_id[0], conn)

    conn.commit()
    conn.close()
    return render_template('user/danhgiathanhcong.html', order_id=order_id)

def get_reviews_from_db(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT comment, sentiment_ai FROM reviews WHERE product_id = ?", (product_id,))
    reviews = cursor.fetchall()
    conn.close()
    return reviews

def summarize_and_update_reviews(product_id, conn):
    # Lấy tất cả các đánh giá từ cơ sở dữ liệu
    reviews = get_reviews_from_db(product_id)
    positive_reviews = []
    negative_reviews = []

    # Phân loại các bình luận thành tích cực và tiêu cực
    for comment, sentiment_ai in reviews:
        if sentiment_ai == "Tích cực":
            positive_reviews.append(comment)
        elif sentiment_ai == "Tiêu cực":
            negative_reviews.append(comment)

    # Tạo tóm tắt cho các bình luận tích cực và tiêu cực
    positive_summary = generate_summary(positive_reviews, "Tích cực")
    negative_summary = generate_summary(negative_reviews, "Tiêu cực")

    # Cập nhật tóm tắt vào cơ sở dữ liệu
    conn.execute('''
        UPDATE products
        SET positive_summary = ?, negative_summary = ?
        WHERE product_id = ?
    ''', (positive_summary, negative_summary, product_id))


# Function to generate summary using Google Generative AI chat
def generate_summary(reviews, sentiment_label):
    if not reviews:
        return f"Không có bình luận cảm xúc {sentiment_label.lower()}."
    
    prompt = f"Tóm tắt các bình luận cảm xúc {sentiment_label.lower()} sau:\n" + "\n".join(reviews)
    chat_session = model.start_chat(history=[])
    response = chat_session.send_message(prompt)
    
    return response.text

@app.route('/donhang/<int:order_id>/suadanhgia')
def update_order(order_id):
    conn = get_db_connection()
    
    # Lấy thông tin các sản phẩm trong đơn hàng
    order_items = conn.execute('''
        SELECT i.order_item_id, i.product_variant_id, pv.product_id, p.name, pv.storage, pv.color, i.quantity, i.price * i.quantity AS total_price
        FROM order_items i
        JOIN product_variants pv ON i.product_variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        WHERE i.order_id = ?
    ''', (order_id,)).fetchall()
    
    # Lấy đánh giá cho từng sản phẩm trong đơn hàng (nếu có)
    reviews = conn.execute('''
        SELECT r.product_variant_id, r.sentiment, r.rating, r.comment
        FROM reviews r
        WHERE r.order_item_id IN (
            SELECT i.order_item_id FROM order_items i WHERE i.order_id = ?
        )
    ''', (order_id,)).fetchall()
    
    conn.close()

    # Kiểm tra nếu không có sản phẩm nào trong đơn hàng
    if not order_items:
        return "Đơn hàng không tồn tại hoặc không có sản phẩm nào", 404

    # Render trang với thông tin đơn hàng và đánh giá
    return render_template('user/suadanhgia.html', order_id=order_id, order_items=order_items, reviews=reviews)





@app.route('/admin/qldonhang/', defaults={'status_id': None}, methods=['GET'])
@app.route('/admin/qldonhang/<int:status_id>', methods=['GET'])
def orders(status_id):
    # Kết nối đến cơ sở dữ liệu
    conn = get_db_connection()

    # Truy vấn đơn hàng kèm theo trạng thái
    if status_id is None:
        orders = conn.execute('''
            SELECT o.*, s.status_name
            FROM orders o
            LEFT JOIN order_statuses s ON o.order_status_id = s.status_id
        ''').fetchall()  # Lấy tất cả đơn hàng
    else:
        orders = conn.execute('''
            SELECT o.*, s.status_name
            FROM orders o
            LEFT JOIN order_statuses s ON o.order_status_id = s.status_id
            WHERE o.order_status_id = ?
        ''', (status_id,)).fetchall()  # Lấy đơn hàng theo trạng thái
    
    # Truy vấn tất cả trạng thái đơn hàng để hiển thị trong template
    order_statuses = conn.execute('SELECT * FROM order_statuses LIMIT 5').fetchall()

    conn.close()  # Đóng kết nối

    return render_template('admin/qldonhang.html', orders=orders,  statusid=status_id, order_statuses=order_statuses)

@app.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    new_status = request.form.get('new_status')  # Nhận trạng thái mới từ form

    conn = get_db_connection()
    
    # Kiểm tra nếu new_status và order_id hợp lệ
    if new_status and order_id:
        conn.execute('''
            UPDATE orders
            SET order_status_id = (SELECT status_id FROM order_statuses WHERE status_name = ?)
            WHERE order_id = ?
        ''', (new_status, order_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})  # Trả về chỉ thông tin thành công
    
    conn.close()
    return jsonify({'success': False})  # Trả về thông tin lỗi


# Route to view order details
@app.route('/orders/<int:order_id>', methods=['GET'])
def view_orders(order_id):
    conn = get_db_connection()

    # Truy vấn thông tin chi tiết đơn hàng
    # Truy vấn để lấy thông tin từ bảng `orders`
    order = conn.execute('''
        SELECT o.*, s.status_name
        FROM orders o
        LEFT JOIN order_statuses s ON o.order_status_id = s.status_id
        WHERE o.order_id = ? 
    ''', (order_id)).fetchone()

    # Truy vấn để lấy thông tin từ bảng `order_items`
    ordersi = conn.execute('''
        SELECT i.product_variant_id, pv.product_id, p.name, pv.storage, pv.color, i.quantity, i.price*i.quantity as total_price
        FROM order_items i
        JOIN product_variants pv ON i.product_variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        WHERE i.order_id = ?
    ''', (order_id,)).fetchall()
    conn.close()

    conn.close()

    # Kiểm tra xem đơn hàng có tồn tại không
    if order is None:
        return "Đơn hàng không tồn tại", 404

    return render_template('admin/ctdonhang.html', ordersi=ordersi, order = order)

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Xử lý thêm sản phẩm
    if request.method == 'POST':
        if 'add_product' in request.form:
            product_name = request.form['product_name']
            description = request.form['description']
            price = request.form['price']
            category_id = request.form['category_id']
            image_url = request.form['image_url']

            cursor.execute("""
                INSERT INTO products (name, description, price, category_id, image_url)
                VALUES (?, ?, ?, ?, ?)
            """, (product_name, description, price, category_id, image_url))
            conn.commit()
            flash('Sản phẩm đã được thêm thành công!', 'success')
        elif 'edit_product' in request.form:
            product_id = request.form['product_id']
            product_name = request.form['product_name']
            description = request.form['description']
            price = request.form['price']
            category_id = request.form['category_id']
            image_url = request.form['image_url']

            cursor.execute("""
                UPDATE products
                SET name = ?, description = ?, price = ?, category_id = ?, image_url = ?
                WHERE product_id = ?
            """, (product_name, description, price, category_id, image_url, product_id))
            conn.commit()
            flash('Sản phẩm đã được cập nhật!', 'success')

   # Xử lý xóa sản phẩm
    if request.method == 'POST' and 'delete_product_id' in request.form:
        product_id = request.form['delete_product_id']
        cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.commit()
        flash('Sản phẩm đã được xóa!', 'success')

    # Lấy danh sách danh mục
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    # Lấy danh sách sản phẩm (theo danh mục nếu có)
    selected_category_id = request.args.get('category_id')
    if selected_category_id:
        cursor.execute("SELECT * FROM products WHERE category_id = ?", (selected_category_id,))
    else:
        cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    return render_template('admin/ad.html', products=products, categories=categories, selected_category_id=selected_category_id)

@app.route('/admin/products/add', methods=['POST'])
def add_product():
    # Lấy dữ liệu từ form modal
    product_name = request.form['product_name']
    description = request.form['description']
    price = request.form['price']
    category_id = request.form['category_id']
    image_url = request.form['image_url']

    # Thêm sản phẩm vào database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (name, description, price, category_id, image_url)
        VALUES (?, ?, ?, ?, ?)
    """, (product_name, description, price, category_id, image_url))
    conn.commit()
    conn.close()

    # Chuyển hướng về trang quản lý sản phẩm
    return redirect(url_for('admin_products'))

@app.route('/admin/comments', methods=['GET', 'POST'])
def admin_comments():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    category_id = request.args.get('category_id')
    product_id = request.args.get('product_id')
    
    # Fetch categories
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    # Fetch products for the selected category
    if category_id:
        cursor.execute("""
            SELECT p.*, c.name 
            FROM products p
            JOIN categories c ON p.category_id = c.category_id 
            WHERE c.category_id = ?
        """, (category_id,))
    else:
        cursor.execute("""
            SELECT p.*, c.name 
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
        """)
    
    products = cursor.fetchall()

    # Create a new list of products with sentiment counts
    product_list = []
    sentiment_distribution = {'Tích cực': 0, 'Trung lập': 0, 'Tiêu cực': 0}
    total_reviews = 0  # Initialize total reviews
    for product in products:
        product_dict = dict(product)
        product_dict['sentiment_counts'] = {'Tích cực': 0, 'Trung lập': 0, 'Tiêu cực': 0}

        # Fetch reviews for the current product
        cursor.execute("""
            SELECT sentiment_ai FROM reviews
            WHERE product_id = ?
        """, (product['product_id'],))
        product_reviews = cursor.fetchall()

        # Calculate sentiment counts for the current product
        for review in product_reviews:
            sentiment = review['sentiment_ai'] if review['sentiment_ai'] in product_dict['sentiment_counts'] else 'Trung lập'
            product_dict['sentiment_counts'][sentiment] += 1
            sentiment_distribution[sentiment] += 1
            total_reviews += 1  # Increment total reviews

        product_list.append(product_dict)

    # Initialize overall sentiment counts
    sentiment_counts = sentiment_distribution.copy()

    conn.close()

    return render_template('admin/adcom.html', 
                           products=product_list, 
                           categories=categories, 
                           sentiment_counts=sentiment_counts, 
                           total_reviews=total_reviews,  # Pass total reviews to template
                           selected_product_id=product_id, 
                           selected_category_id=category_id
                           )

@app.route('/admin/comment/', defaults={'category_id': None, 'product_id': None}, methods=['GET', 'POST'])
@app.route('/admin/comment/category/<int:category_id>', methods=['GET', 'POST'])
@app.route('/admin/comment/product/<int:product_id>', methods=['GET', 'POST'])
def admin_commentss(category_id=None, product_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    selected_category_id = None
    selected_product_id = None
    # Lấy danh sách các danh mục
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    # Nếu có product_id, lấy bình luận theo product_id
    if product_id is not None:
        cursor.execute("SELECT r.*, p.name FROM reviews r JOIN products p ON r.product_id = p.product_id WHERE r.product_id = ?", (product_id,))
        reviews = cursor.fetchall()
        selected_product_id = product_id
    # Nếu có category_id, lấy bình luận theo category_id
    elif category_id is not None:
        cursor.execute("""SELECT r.*, p.name FROM reviews r
                          JOIN products p ON r.product_id = p.product_id
                          WHERE p.category_id = ?""", (category_id,))
        reviews = cursor.fetchall()
        selected_category_id = category_id
        selected_product_id = None  # Không có sản phẩm cụ thể
    else:
        # Nếu không có cả product_id và category_id, lấy tất cả bình luận
        cursor.execute("SELECT r.*, p.name FROM reviews r JOIN products p ON r.product_id = p.product_id")
        reviews = cursor.fetchall()
        selected_category_id = None
        selected_product_id = None

    conn.close()

    return render_template('admin/adcomct.html', categories=categories, reviews=reviews, selected_category_id=selected_category_id, selected_product_id=selected_product_id)

@app.route('/admin/update_admin_review/<int:id>', methods=['POST'])
def admin_update_sentiment(id):
    # Kết nối đến cơ sở dữ liệu
    conn = get_db_connection()
    cursor = conn.cursor()

    # Lấy cảm xúc từ biểu mẫu
    admin_sentiment = request.form.get('admin_sentiment')
    
    # Cập nhật đánh giá quản trị nếu id và admin_sentiment được cung cấp
    if id and admin_sentiment:
        cursor.execute("""
            UPDATE reviews
            SET sentiment_ad = ?
            WHERE id = ?
        """, (admin_sentiment, id))
        conn.commit()
        
        # Có thể thêm thông báo thành công ở đây
        conn.close()
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False})






@app.route('/download_reviews/<int:product_id>')
def download_reviews(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews WHERE product_id = ?", (product_id,))
    reviews = cursor.fetchall()
    conn.close()

    # Convert reviews to CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Review ID', 'Product ID', 'Customer ID', 'Rating', 'Comment', 'Sentiment', 'Sentiment AI','Sentiment AD', 'Review Date'])
    for review in reviews:
        writer.writerow([review['id'], review['product_id'], review['user_id'], review['rating'], review['comment'], review['sentiment'], review['sentiment_ai'],review['sentiment_ad'], review['created_at']])
    
    output.seek(0)
    
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename=reviews_product_{product_id}.csv"})

@app.route('/admin/download_reviews/', defaults={'category_id': None})
@app.route('/admin/download_reviews/<int:category_id>')
def download_all_reviews(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if category_id:
        # Fetch reviews by category_id
        cursor.execute("""
            SELECT * FROM reviews
            JOIN products ON reviews.product_id = products.product_id
            WHERE products.category_id = ?
        """, (category_id,))
        reviews = cursor.fetchall()
    else:
        # Fetch all reviews
        cursor.execute("SELECT * FROM reviews")
        reviews = cursor.fetchall()

    # Convert reviews to CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Review ID', 'Product ID', 'Customer ID', 'Rating', 'Comment', 'Sentiment', 'Sentiment AI','Sentiment AD', 'Review Date'])
    for review in reviews:
        writer.writerow([review['id'], review['product_id'], review['user_id'], review['rating'], review['comment'], review['sentiment'], review['sentiment_ai'],review['sentiment_ad'], review['created_at']])
    
    output.seek(0)
    
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=all_reviews.csv"})

if __name__ == '__main__':
    app.run(debug=True)
