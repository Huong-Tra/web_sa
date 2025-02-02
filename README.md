# Mô tả sản phẩm đề tài: Thử nghiệm một số mô hình phân loại cảm xúc văn bản và Ứng dụng vào Website bán lẻ di động

## 1. Giới thiệu

Sản phẩm này bao gồm một thư mục **Model phân loại cảm xúc** với ba mô hình **CNN (Convolutional Neural Network)**, **biLSTM (Bidirectional Long Short-Term Memory)**, và sự kết hợp giữa **CNN và biLSTM** dùng để phân loại cảm xúc văn bản trong các đánh giá của khách hàng trên website mua sắm Tiki.vn. Những mô hình này được thử nghiệm để phân loại các đánh giá vào các nhóm cảm xúc chính: **Tích cực**, **Tiêu cực**, và **Trung lập**. 

Bên cạnh đó, sản phẩm còn tích hợp mô hình phân loại vào một **website bán lẻ di động**, giúp cải thiện trải nghiệm người dùng thông qua việc phân tích cảm xúc của các đánh giá và phản hồi một cách nhanh chóng và chính xác.

## Model phân loại cảm xúc

Đây là thư mục chính chứa ba mô hình học máy (CNN, biLSTM, CNN-biLSTM) cũng như phương thức thu thập dữ liệu là các bình luận về mặt hàng di động điện tử trên trang Tiki.vn. Mỗi mô hình và đoạn code thu thập dữ liệusẽ được lưu trữ trong một thư mục con riêng biệt, bao gồm các file huấn luyện, dữ liệu, mô hình đã huấn luyện và các công cụ hỗ trợ.

### Thu thập dữ liệu:
Việc thu thập dữ liệu sẽ được tiến hành thông qua request bằng cách thu thập các thông tin liên quan đến sản phẩm trước như id, nội dung mô tả các bình luận sau đó tương ứng với từng sản phẩm sẽ thu thập danh sách bình luận
- crawl_idsp.py: các hàm để thu thập dữ liệu về id các sản phẩm trong danh mục Điện thoại - Máy tính bảng
-  crawl_ttsp.py: các hàm thu thập thông tin liên quan đến sản phẩm theo id tương ứng
-  crawl_comment: các hàm thu thập thông tin các bình luận về sản phẩm theo id tương ứng

### Mô hình CNN:
- modelcnn.ipynb: Script huấn luyện và triển khai mô hình CNN. Bao gồm các hàm xây dựng mô hình, huấn luyện, và đánh giá hiệu suất.
- datatrain.xlsx: Bộ dữ liệu được thu thập từ Tiki.vn phục vụ cho việc đào tạo và test mô hình. Dữ liệu trong tập được chia thành 2 tập train và test tỉ lệ 80:20
- dulieumoi.xlsx: Dữ liệu thêm vào để đánh giá mô hình.
- tokenizer_data.pkl: File lưu trữ bộ tokenizer (vocabularies và thông tin chuẩn hóa văn bản). File này được sử dụng để mã hóa dữ liệu văn bản đầu vào trước khi đưa vào mô hình.
- model_cnn.keras: Mô hình đã huấn luyện, được lưu dưới định dạng .keras để dễ dàng tái sử dụng.

### Mô hình BiLSTM:
- modelbilstm.ipynb: Script huấn luyện và triển khai mô hình BiLSTM. Bao gồm các hàm xây dựng mô hình, huấn luyện, và đánh giá hiệu suất.
- datatrain.xlsx: Bộ dữ liệu được thu thập từ Tiki.vn phục vụ cho việc đào tạo và test mô hình. Dữ liệu trong tập được chia thành 2 tập train và test tỉ lệ 80:20
- dulieumoi.xlsx: Dữ liệu thêm vào để đánh giá mô hình.
- tokenizer_data.pkl: File lưu trữ bộ tokenizer (vocabularies và thông tin chuẩn hóa văn bản). File này được sử dụng để mã hóa dữ liệu văn bản đầu vào trước khi đưa vào mô hình.
- model_lstm.keras: Mô hình đã huấn luyện, được lưu dưới định dạng .keras để dễ dàng tái sử dụng.

### Mô hình CNN - BiLSTM:
- model_cnn_bilstm.ipynb: Script huấn luyện và triển khai mô hình CNN - biLSTM. Bao gồm các hàm xây dựng mô hình, huấn luyện, và đánh giá hiệu suất.
- datatrain.xlsx: Bộ dữ liệu được thu thập từ Tiki.vn phục vụ cho việc đào tạo và test mô hình. Dữ liệu trong tập được chia thành 2 tập train và test tỉ lệ 80:20
- dulieumoi.xlsx: Dữ liệu thêm vào để đánh giá mô hình.
- tokenizer_data.pkl: File lưu trữ bộ tokenizer (vocabularies và thông tin chuẩn hóa văn bản). File này được sử dụng để mã hóa dữ liệu văn bản đầu vào trước khi đưa vào mô hình.
- modelcnn_bilstm.keras: Mô hình đã huấn luyện, được lưu dưới định dạng .keras để dễ dàng tái sử dụng.

## Website bán lẻ di động

Đây là thư mục chính chứa  website bán lẻ di động có tích hợp mô hình học máy bao gồm các thư mục database, html, css, javascript, và các file phục vụ việc tích hợp mô hình

## bd
Thư mục lưu trữ database với csdl.db được tạo với SQL Lite với các bảng cần thiết phục vụ co các tác vụ cơ bản của một website thông thường 

## static
Thư mục lưu trữ các file .css, ảnh và javascript mỗi nội dung đều được đưa vào thư mục tương ứng phục vụ việc xây dựng giao diện hệ thống

## templates
Thư mục lưu trữ các .html với 2 thư mục user và admin phục vụ việc xây dựng giao diện hệ thống với 2 đối tượng người dùng khác nhau

## main.py
File chính của ứng dụng web, sử dụng Flask để triển khai hệ thống website với các chwucs năng cơ bản của một website thông thường nhưng sẽ tập trung vào các chức năng phân loại cảm xúc với việc tích hợp các mô hình phân loại cảm xúc cũng như gọi đến Gemini thông qua API.

## File phục vụ việc phân loại cảm xúc
- tokenizer_data.pkl: File lưu trữ bộ tokenizer (vocabularies và thông tin chuẩn hóa văn bản). File này được sử dụng để mã hóa dữ liệu văn bản đầu vào trước khi đưa vào mô hình được lấy từ kết quả sau khi thực hiện xử lí dữ liệu.
- modelcnn_bilstm.keras/modelcnn.keras/modelbilstm.keras: Mô hình đã huấn luyện, được lưu dưới định dạng .keras để dễ dàng tái sử dụng.

### Các thư viện cần thiết cho việc đào tạo các mô hình, xây dựng website
- tensorflow
- keras
- flask
- numpy
- pandas
- scikit-learn
- matplotlib
