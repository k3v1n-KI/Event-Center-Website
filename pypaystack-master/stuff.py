# from pypaystack import transactions
# from pypaystack.transactions import Transaction
# from datetime import datetime

# def toDateTime(html_dtObject):
#     date_processing = html_dtObject.replace(
#         'T', '-').replace(':', '-').replace(".000Z", "").split('-')
#     date_processing = [int(v) for v in date_processing]
#     date_out = datetime(*date_processing)
#     return date_out

# transactions = Transaction(authorization_key="sk_test_7e4d1f1b634b8817e2eb350f9bc4465b4c6c6295")
# response = transactions.verify(889851935)
# paid_datetime_formated = toDateTime(response[3]["paid_at"])
# print(int(response[3]["amount"] / 100))
def is_power_of_two(n):
  # Check if the number can be divided by two without a remainder
  while n % 2 == 0:
    if n == 0:
      return False
    n = n / 2
  # If after dividing by two the number is 1, it's a power of two
    return True
  return False
  

print(is_power_of_two(0)) # Should be False
print(is_power_of_two(1)) # Should be True
print(is_power_of_two(8)) # Should be True
print(is_power_of_two(9)) # Should be False