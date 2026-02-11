def unsafe_eval(user_input):
    result = eval(user_input)  # Using eval() unsafely
    return result

user_input = input("Enter an expression to evaluate: ")
print(unsafe_eval(user_input))
