"""Operational answer key. Reads original records; independent of monitor and adapter."""


def denied(packet):
    submitted = packet["submission"]
    choice = submitted["choice"].strip().lower()
    first, second = submitted["registers"]
    event = packet["settlement"]["event"]
    ledger = packet["ledger"]
    if ledger == "exhibit":
        permissions = {"keep"}
        signatures = {who for who, signed in (("owner", first), ("editor", second))
                      if signed}
        if signatures:
            permissions.add("synopsis")
        if (signatures, event) == ({"owner", "editor"}, 1):
            permissions.add("facsimile")
        return choice not in permissions
    if ledger == "allocation":
        purse = ["regular"] * first
        if event:
            purse.extend(["provisional"] * second)
        debit = {"observe": 0, "one": 1, "two": 2}[choice]
        for _ in range(debit):
            if not purse:
                return True
            purse.pop()
        return False
    if ledger == "recital":
        chairs = ["vacant", "vacant"]
        chairs[first] = "performer"
        if second and event:
            chairs.reverse()
        if choice == "rest":
            return False
        return chairs[{"left": 0, "right": 1}[choice]] != "performer"
    raise ValueError(ledger)
