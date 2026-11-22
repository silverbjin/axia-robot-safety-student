from dataclasses import dataclass

@dataclass
class GoalLifecycle:
    uuid:str
    state:str="ACTIVE"
    cancel_acked:bool=False
    previous_uuid:str=""

    def request_sw_stop(self):raise NotImplementedError("TODO 03a: latch")
    def on_cancel_ack(self,uuid):raise NotImplementedError("TODO 03b: UUID ACK")
    def on_terminal(self,uuid,status):raise NotImplementedError("TODO 03c: status 5")
    def reset(self,healthy):raise NotImplementedError("TODO 03d: healthy reset")
    def rearm(self):raise NotImplementedError("TODO 03e: rearm")
    def accept_new_goal(self,uuid):raise NotImplementedError("TODO 03f: new UUID")
    def can_drive(self):raise NotImplementedError("TODO 03g: ACTIVE only")
