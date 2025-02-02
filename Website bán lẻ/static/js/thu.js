document.addEventListener('DOMContentLoaded', function () {
    // Safely pass reviews data from Flask to JavaScript
    const reviews = JSON.parse('{{ reviews|tojson|safe }}');
    
    let totalRating = 0;
    let numberOfReviews = reviews.length;

    if (numberOfReviews > 0) {
        reviews.forEach(review => {
            totalRating += review.rating;
        });

        let averageRating = (totalRating / numberOfReviews).toFixed(1);
        document.getElementById('averageRating').innerText = averageRating;
    } else {
        document.getElementById('averageRating').innerText = "Chưa có đánh giá";
    }
});