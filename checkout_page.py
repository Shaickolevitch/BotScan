CHECKOUT_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>BotScan Checkout</title>
    <script src="https://cdn.paddle.com/paddle/v2/paddle.js"></script>
    <style>
        body {{ background:#0f1117; display:flex; justify-content:center; 
               align-items:center; height:100vh; margin:0; }}
        p {{ color:white; font-family:sans-serif; font-size:18px; }}
    </style>
</head>
<body>
    <p>⏳ Opening secure checkout...</p>
    <script>
        Paddle.Initialize({{ token: '{token}' }});
        Paddle.Checkout.open({{
            transactionId: '{txn_id}',
            settings: {{ successUrl: '{success_url}' }}
        }});
    </script>
</body>
</html>"""