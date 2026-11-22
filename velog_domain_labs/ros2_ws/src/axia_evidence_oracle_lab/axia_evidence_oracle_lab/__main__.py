from .core import evaluate_stop_evidence

def main():
    print(evaluate_stop_evidence({"actual_gazebo_executed":False}))

if __name__=="__main__":main()
