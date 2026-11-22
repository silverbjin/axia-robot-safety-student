from .core import guard_decision

def main():
    print(guard_decision(10,9.80,0.02,[]).reason)

if __name__=="__main__":main()
