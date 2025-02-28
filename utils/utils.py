def calculate_product_cost(price, yuan_rate):
    commission = 0.15 if price <= 300 else 0.10 if price <= 500 else 0.05
    commission_amount = price * commission
    final_cost = (price + commission_amount) * yuan_rate
    return round(final_cost, 2), round(commission_amount, 2)

def calculate_shipping_cost(length, width, height, weight, yuan_rate):
    volume_weight = (length * width * height) / 5000
    actual_weight = weight
    used_weight = max(volume_weight, actual_weight)
    cost_usd = used_weight * 8  # Стоимость доставки за 1 кг (8 долларов)
    cost_rub = cost_usd * yuan_rate
    return round(cost_usd, 2), round(cost_rub, 2)
