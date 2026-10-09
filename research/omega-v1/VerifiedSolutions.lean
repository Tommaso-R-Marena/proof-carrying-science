-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=6d2d2a44c1b7fc72d76efa8e80148f71a8fd94645bfd6ee89b8c289b12d129e1
theorem omega_equivalence_1 (p0 p1 p2 p3 : Bool) :
    (!(p2 && p2)) = ((!p2) || (!p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_1

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=33bd000318ea5b3e4f5b137376c2bf5de11be34a4a3fff2cd8ac0dc61347bc47
theorem omega_equivalence_2 (p0 p1 p2 p3 : Bool) :
    (!(p1 && p0)) = ((!p1) || (!p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_2

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=5e286114463c0765ade5486c8bfcecb4a37f6b5f9ec3d7eb182ae331b3c9e71b
theorem omega_equivalence_5 (p0 p1 p2 p3 : Bool) :
    (!(p1 && (!p0))) = ((!p1) || (!(!p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_5

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e0abb0c97af83911c110dc4781212172e241ca9d8a9db900e8d4d6f6cd6df7a8
theorem omega_equivalence_8 (p0 p1 p2 p3 : Bool) :
    (!(p0 && (!(p0 && p0)))) = ((!(!p0)) || (!(p0 && p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_8

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b249981ff2d39ca676730bae3a5732e18ba7ae0f648e36ce5c47744c9e50b9a6
theorem omega_equivalence_15 (p0 p1 p2 p3 : Bool) :
    (!(p2 && (!(!p2 || p3) || (!p2 || p3)))) = ((!p2) && (!(!p2 || p3) || (!p2 || p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_15

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=55a8d62a71006231a1234e8a91c311819a92eeac82dc28aac2c1bc2d5650487c
theorem omega_equivalence_19 (p0 p1 p2 p3 : Bool) :
    (!((!(!p3) || (!p3 || p0)) && (!(p0 || p2)))) = (!((!(!(!p3) || (!p3 || p0))) || (!(p0 || p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_19

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=68799e8c0da9123544a7db2e204f863779b7290ceedcfe97a1561592d2cf5688
theorem omega_equivalence_23 (p0 p1 p2 p3 : Bool) :
    (!(p2 && ((!p1) && (p2 || p3)))) = ((!p2) || ((!(!p1)) && (p2 || p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_23

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=02a04b3a42290011a5de38ae0ea861f490c0fde420d59ef2e8008691eb914c9b
theorem omega_equivalence_24 (p0 p1 p2 p3 : Bool) :
    (!(p1 && (p0 && p3)) || p1) = (!(p1 && (p0 && p3)) || p1) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_24

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e14d9268f802b0da2c3c98a10675e04552d9201afa9f65999808e81b8e36866a
theorem omega_equivalence_25 (p0 p1 p2 p3 : Bool) :
    (!(!(!p3 || p2)) || (!p2 || p3)) = ((!(!(!p3 || p2))) || (!p2 || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_25

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=12e51c2a70f7e3d01008e7a9de54396bb367ee874ae1f1a622629dafc26e01b3
theorem omega_equivalence_26 (p0 p1 p2 p3 : Bool) :
    (!(p1 || p1) || p1) = (!(p1 || p1) || p1) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_26

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=c99c06fa956f8203f5e5b5077ecfc78baa499e71487146f9cb9bb4aafd51291e
theorem omega_equivalence_27 (p0 p1 p2 p3 : Bool) :
    (!p1 || (!(p0 || p0))) = (!p1 || (!(p0 || p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_27

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=2f6d804c01ac23021ab4dafe204f3fcc8121d99f2c7f0e5b37889d0e997e1f5c
theorem omega_equivalence_28 (p0 p1 p2 p3 : Bool) :
    (!(p2 || (p0 && p1)) || (!p3)) = (!(p2 || (p0 && p1)) || (!p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_28

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=404a7d2cc81d9724d960b19d60c6d90eef2e850ab939039fd8dd75c2e818e5ea
theorem omega_equivalence_29 (p0 p1 p2 p3 : Bool) :
    (!(!(p1 && p0) || p2) || (!p1 || (p1 && p2))) = (!(!(p1 && p0) || p2) || (!p1 || (p1 && p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_29

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=d654cf27779a67031edd66b6b9e9939d92cc14ab388484570fb7ab5ee0b02a2d
theorem omega_equivalence_30 (p0 p1 p2 p3 : Bool) :
    (!(p0 || (p2 && p2)) || (p2 || p2)) = (!(p0 || (p2 && p2)) || (p2 || p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_30

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f34362b79aeab24d9d0c9e5ceed6ba283a91f1d9232f4553dd7044eab71212e8
theorem omega_equivalence_31 (p0 p1 p2 p3 : Bool) :
    (!p2 || (!p3 || p0)) = (!p2 || (!p3 || p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_31

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=d1f07ff0f7936b2aeca51bfaabf12b7c5901c81c25b04592667b3f63d7714ced
theorem omega_equivalence_32 (p0 p1 p2 p3 : Bool) :
    (!p0 || (!(p1 && p0) || (p2 || p2))) = (!p0 || (!(p1 && p0) || (p2 || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_32

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=2d8eac3283160c96ccc45232fa460bf8fe634631670d49575654b80a26ab965d
theorem omega_equivalence_33 (p0 p1 p2 p3 : Bool) :
    (!((p3 && p3) && p0) || p1) = (!((p3 && p3) && p0) || p1) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_33

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=c1b14371e171f2cbbf405d149a3eedd57b520be0495352229e0858d09f51f63a
theorem omega_equivalence_34 (p0 p1 p2 p3 : Bool) :
    (!(p3 || (!p1 || p0)) || p2) = (!(p3 || (!p1 || p0)) || p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_34

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=55010e630a348e0610207b5d682c9f533f2d3a49d1e630d94d49da9d24937b66
theorem omega_equivalence_35 (p0 p1 p2 p3 : Bool) :
    (!p1 || (p3 || (!p0 || p2))) = (!p1 || (p3 || (!p0 || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_35

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=3134c3223f22b40fa1da127f08fff92dd1b4be1f51ca7d2db082d63066828a51
theorem omega_equivalence_36 (p0 p1 p2 p3 : Bool) :
    (!(!(p3 || p3)) || p2) = ((!(!(p3 || p3))) || p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_36

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=209f535e4973b40119340d5adafd7b4e01c4b1e8b5961d6710f5a71817c274ef
theorem omega_equivalence_37 (p0 p1 p2 p3 : Bool) :
    (!(!(!p0)) || (!(p3 && p0))) = ((!(!(!p0))) || (!(p3 && p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_37

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=db251415e35b0208e2f21c46110463437922688bfff1dfdc7ee4bc5ded6b7355
theorem omega_equivalence_38 (p0 p1 p2 p3 : Bool) :
    (!((p1 && p1) && p2) || ((!p3) || p0)) = (!((p1 && p1) && p2) || ((!p3) || p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_38

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=45e9d4b4dfd76ac345136d09efa1c27df7cad4def9c6148886083ebe9a3302d2
theorem omega_equivalence_39 (p0 p1 p2 p3 : Bool) :
    (!(!(!p0) || p3) || p2) = (!(!(!p0) || p3) || p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_39

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=c75230b72d14e55febf275e290e3d910364aa74cd5e0cb192c1da6a7fd6791d5
theorem omega_equivalence_40 (p0 p1 p2 p3 : Bool) :
    (!((p2 || p2) && (!p2)) || p1) = (!((p2 || p2) && (!p2)) || p1) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_40

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=d099a52a271cfc6258bd5b596b8a01263910bc9ffe674e4d3ed4ba3f7f628dfe
theorem omega_equivalence_41 (p0 p1 p2 p3 : Bool) :
    (!(!(p2 || p1)) || (!(p2 && p2) || p1)) = ((!(!(p2 || p1))) || (!(p2 && p2) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_41

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=5683b8329148d05e4c395162ae58705a67518c9e85a887797e46cb3e77f1673d
theorem omega_equivalence_42 (p0 p1 p2 p3 : Bool) :
    (!(p3 || p3) || (p2 && p3)) = (!(p3 || p3) || (p2 && p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_42

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=53917e4e143c1f003d329b1eac772ceae8b55f941e05965b8d8a08ab85bab685
theorem omega_equivalence_43 (p0 p1 p2 p3 : Bool) :
    (!(p3 && p3) || (!(p1 && p1) || (!p0 || p2))) = (!(p3 && p3) || (!(p1 && p1) || (!p0 || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_43

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e562d50032331c8ce8311f5b14bf6d6c821a179b18824db68643268269690ab1
theorem omega_equivalence_44 (p0 p1 p2 p3 : Bool) :
    (!(!(p3 && p0)) || (!p0 || (p1 || p1))) = ((!(!(p3 && p0))) || (!p0 || (p1 || p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_44

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=de3297a6e7b5a2bc403a375bcb5be8d8f83f73ee4eb3325774653537ad054714
theorem omega_equivalence_45 (p0 p1 p2 p3 : Bool) :
    (!p0 || ((p1 || p2) && p1)) = (!p0 || ((p1 || p2) && p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_45

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=398daf36cb66ae6d97d6750d3e60fc6241ab9614f426e2156a40202a4b70ec46
theorem omega_equivalence_46 (p0 p1 p2 p3 : Bool) :
    (!(p3 && p2) || ((!p0 || p3) || (!p0 || p2))) = (!(p3 && p2) || ((!p0 || p3) || (!p0 || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_46

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=ef087f9950bacd690083a854be6b9aa9256ed862c30e8933bbd62ef178551528
theorem omega_equivalence_47 (p0 p1 p2 p3 : Bool) :
    (!(!(p1 || p1) || (!p0 || p1)) || p1) = ((!(p1 || p1) || (!p0 || p1)) && p1) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_47

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=7ff8aba7ad2114513afb74e4758da1ce2b86f8482a36ac3fb2bd25b666481f01
theorem omega_equivalence_54 (p0 p1 p2 p3 : Bool) :
    ((p3 || p1) && (p1 || p1)) = (((p3 || p1) && p1) && ((p3 || p1) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_54

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b76e26e0264db87416a02cc1538b24a2847cc4b4faec40e97e7e516db7c51dbb
theorem omega_equivalence_56 (p0 p1 p2 p3 : Bool) :
    ((!(!p2) || (p0 && p3)) && (p3 || ((!p2) || (!p2)))) = (((!(!p2) || (p0 && p3)) && p3) && ((!(!p2) || (p0 && p3)) || ((!p2) || (!p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_56

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f54c2e1c1b2405ec39fb693c04bd78a6c3dde0c2df2d4c2eaee70aea3e9f8d7f
theorem omega_equivalence_57 (p0 p1 p2 p3 : Bool) :
    ((p1 && (!p1 || p1)) && ((p3 || p1) || (!p0))) = (((p1 && (!p1 || p1)) && (p3 || p1)) && ((p1 && (!p1 || p1)) || (!p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_57

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=a8a082068209b11a3ed3ccf3f38548df2f3a032a4d0ce3a8a29bf8816de66db3
theorem omega_equivalence_58 (p0 p1 p2 p3 : Bool) :
    (p3 && ((!(!p3) || (!p0)) || p1)) = ((p3 && (!(!p3) || (!p0))) && (p3 || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_58

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=3c2952b5ada1c53f9f3f9a0d45444eda9dd508c746eb2749d805b02f5d23091b
theorem omega_equivalence_59 (p0 p1 p2 p3 : Bool) :
    (p1 && ((!(!p0) || (p2 && p2)) || ((!p0 || p1) && (p0 && p2)))) = ((p1 && (!(!p0) || (p2 && p2))) && (p1 || ((!p0 || p1) && (p0 && p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_59

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f55d030cb175708f606319fb75954691c5d8de48cd8e5b14b3eecd64621a94ff
theorem omega_equivalence_61 (p0 p1 p2 p3 : Bool) :
    ((!(p1 || p0) || (p3 && p0)) && (p1 || p1)) = (((!(p1 || p0) || (p3 && p0)) && p1) && ((!(p1 || p0) || (p3 && p0)) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_61

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=95f6746ac175b9deccb7a100f5bedfa6d979eb65700c85bb73144d341dde42e8
theorem omega_equivalence_62 (p0 p1 p2 p3 : Bool) :
    (p2 && ((!(p1 && p1) || (p3 && p1)) || (!(!p3)))) = ((p2 && (!(p1 && p1) || (p3 && p1))) && (p2 || (!(!p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_62

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=d6b10ec40c026340dae29f1378d341cf7afb9c0f6632bbb4ecdbec65db186dc6
theorem omega_equivalence_67 (p0 p1 p2 p3 : Bool) :
    (p3 && (p0 || (!p3 || (p0 && p0)))) = ((p3 && p0) && (p3 || (!p3 || (p0 && p0)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_67

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=cd9094aba6cdeb150af14b574d69a898dd283e2ce3da3271e792901c97c12098
theorem omega_equivalence_68 (p0 p1 p2 p3 : Bool) :
    (p3 && ((p3 && (p3 && p2)) || (!(p0 || p3)))) = ((p3 && (p3 && (p3 && p2))) && (p3 || (!(p0 || p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_68

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=1ff1adb5daf1f93b204f2a387dd9c5370fe3f978effb46a4b30d2e261a2532fd
theorem omega_equivalence_69 (p0 p1 p2 p3 : Bool) :
    ((!(p1 || p2)) && ((p0 && (p2 && p0)) || p1)) = (((!(p1 || p2)) && (p0 && (p2 && p0))) && ((!(p1 || p2)) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_69

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=787e16b686da69657d8bc46fde40369e1a9171f74ffa6cc217e392429de80990
theorem omega_equivalence_70 (p0 p1 p2 p3 : Bool) :
    ((!(!p1 || p1)) && ((p2 && (!p3 || p0)) || p1)) = (((!(!p1 || p1)) && (p2 && (!p3 || p0))) && ((!(!p1 || p1)) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_70

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=eef77f9869632babc7f23fd035d458dd795239b8d254d96c97b4a6a63facf432
theorem omega_equivalence_72 (p0 p1 p2 p3 : Bool) :
    p1 = (p1 && ((!(!p1)) || (!p1 || p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_72

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=4ef2061a8c91ad0b8daad22d6299fc4ab97b02e812a01a0a57f55dffa99af600
theorem omega_equivalence_73 (p0 p1 p2 p3 : Bool) :
    (!(p3 && p1) || (!p3)) = ((!(p3 && p1) || (!p3)) && ((!(!(!(p3 && p1) || (!p3)))) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_73

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f87e623181f499e6dfc605cd528dbc32fcbc94b9844ff4363034bd4c4096901d
theorem omega_equivalence_74 (p0 p1 p2 p3 : Bool) :
    (!(p0 && p1) || p1) = ((!(p0 && p1) || p1) && ((!(!(!(p0 && p1) || p1))) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_74

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f24443fb24ed31246348d734aea9df8bf9df696bb828180f7dd8cb9db6256594
theorem omega_equivalence_75 (p0 p1 p2 p3 : Bool) :
    (!(!p1) || p3) = ((!(!p1) || p3) && ((!(!(!(!p1) || p3))) || (!(!p2 || p1)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_75

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=2c37487c310c91559f4b81c2fdc90cd7507874c18826d7310d62db6a5e4f681d
theorem omega_equivalence_76 (p0 p1 p2 p3 : Bool) :
    ((!p0) && (p1 || p0)) = (((!p0) && (p1 || p0)) && ((!((!(!p0)) && (p1 || p0))) || (p2 && p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_76

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=d8128e858651831ca0f66fc2583007f18e886889fc45d9b9d0eb4f8a2dc4502e
theorem omega_equivalence_77 (p0 p1 p2 p3 : Bool) :
    ((p0 || p2) || p0) = (((p0 || p2) || p0) && ((!(!((p0 || p2) || p0))) || (!p0 || (p2 && p1)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_77

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b496c800430cccbbebbdcd052aff9d0aeb204c23ee36f1fe078e403541c36378
theorem omega_equivalence_78 (p0 p1 p2 p3 : Bool) :
    (!(p1 && p0) || p2) = ((!(p1 && p0) || p2) && ((!(!(!(p1 && p0) || p2))) || (!(p1 || p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_78

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f8a3458dbaf905e382cff0b6e2a81a6b5ba7ae825280c1394dda4e2f035313e4
theorem omega_equivalence_79 (p0 p1 p2 p3 : Bool) :
    ((p0 || p3) || (!p1 || p3)) = (((p0 || p3) || (!p1 || p3)) && ((!(!((p0 || p3) || (!p1 || p3)))) || p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_79

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=782447b002a98d1e8fb2ae326818ce07f2de3790645a4bbc9e6ad93059769cdd
theorem omega_equivalence_80 (p0 p1 p2 p3 : Bool) :
    (!(p2 && p2) || p1) = ((!(p2 && p2) || p1) && ((!(!(!(p2 && p2) || p1))) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_80

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=ba97e3d0ded021546e79e579b610acc91f53b8e02f41e1be604b6a93390369c5
theorem omega_equivalence_81 (p0 p1 p2 p3 : Bool) :
    ((!p2 || p3) || (p3 || p0)) = (((!p2 || p3) || (p3 || p0)) && ((!(!((!p2 || p3) || (p3 || p0)))) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_81

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=3ece2b8aef7d9228ecf2de3d9cf46a1800e27f11ec509bc3fb5c4ab4837a98ef
theorem omega_equivalence_82 (p0 p1 p2 p3 : Bool) :
    (!(p0 || p2) || (p0 && p3)) = ((!(p0 || p2) || (p0 && p3)) && ((!(!(!(p0 || p2) || (p0 && p3)))) || p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_82

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=160387388258317848c010c506d7e82d0baccbf70ee7e4e00cc41c226d38a8fa
theorem omega_equivalence_83 (p0 p1 p2 p3 : Bool) :
    (p0 && (p1 || p0)) = ((p0 && (p1 || p0)) && ((!(!(p0 && (p1 || p0)))) || (!p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_83

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=46c915dc3478c044e0b729b7f8562e6b48e3c8c4ce8525a74aa008376e53e162
theorem omega_equivalence_84 (p0 p1 p2 p3 : Bool) :
    (p1 || (!p0 || p0)) = ((p1 || (!p0 || p0)) && ((!(!(p1 || (!p0 || p0)))) || (p3 && (!p1)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_84

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=8c98b8f6747e93e296b5f3cccc1ae1e7821206c4575e7a0fb4d39659a5ed2895
theorem omega_equivalence_85 (p0 p1 p2 p3 : Bool) :
    ((!p2 || p3) || (!p1)) = (((!p2 || p3) || (!p1)) && ((!(!((!p2 || p3) || (!p1)))) || ((p0 || p0) && (p2 || p1)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_85

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=adc3251303779f502a19ec7fc0d349ae27cf9d40dd7d93dae9a61045312d406e
theorem omega_equivalence_86 (p0 p1 p2 p3 : Bool) :
    ((!p3 || p0) || p0) = (((!p3 || p0) || p0) && ((!(!((!p3 || p0) || p0))) || ((p3 || p2) || p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_86

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=d2266c07790497e8d3e37e05a66809fb14d2b03bd354c571cecc6cd9d8af5019
theorem omega_equivalence_87 (p0 p1 p2 p3 : Bool) :
    (p0 && (!p1)) = ((p0 && (!p1)) && ((!(!(p0 && (!p1)))) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_87

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=2e204371f00252188709127df81504810b410055c78b0e2e2bd26188fe40cf8a
theorem omega_equivalence_88 (p0 p1 p2 p3 : Bool) :
    ((p3 && p0) && (p0 && p0)) = (((p3 && p0) && (p0 && p0)) && ((!(!((p3 && p0) && (p0 && p0)))) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_88

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=6405e0a124af234ed7eb03f8fd85b8289e04b7c060b490660ec7994c2be03128
theorem omega_equivalence_89 (p0 p1 p2 p3 : Bool) :
    (!(p3 && p1) || (p2 || p3)) = ((!(p3 && p1) || (p2 || p3)) && ((!(!(!(p3 && p1) || (p2 || p3)))) || (!p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_89

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e0b9409f5d6884fe14c2d151322c241f72acc49f94fa0241e6b9084f3bc26305
theorem omega_equivalence_90 (p0 p1 p2 p3 : Bool) :
    ((p2 || p2) || p2) = (((p2 || p2) || p2) && ((!(!((p2 || p2) || p2))) || (!(!p2 || p2) || (!p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_90

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=7b504a033d4fea524f5b66f8e98ad855bf0d0d4e7821a6d59f43b997d5eb8a6d
theorem omega_equivalence_91 (p0 p1 p2 p3 : Bool) :
    (p0 || p3) = ((p0 || p3) && ((!(!(p0 || p3))) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_91

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=4ec94b252bc540818d598d0fa0b3dd9cbab32e3dc8f94b688e351b542ccd4d11
theorem omega_equivalence_92 (p0 p1 p2 p3 : Bool) :
    (!(!p2 || p2) || (!p0 || p1)) = ((!(!p2 || p2) || (!p0 || p1)) && ((!(!(!(!p2 || p2) || (!p0 || p1)))) || (p2 && p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_92

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=5d7b91a794ee2ee720652f3a01599e6cddd502199489acb96cc39ef5342cbeaf
theorem omega_equivalence_93 (p0 p1 p2 p3 : Bool) :
    ((!p2 || p0) || (!p2)) = (((!p2 || p0) || (!p2)) && ((!(!((!p2 || p0) || (!p2)))) || (!(!p2 || p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_93

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=ec0c15eff66e3f3796bea46fc17cab7cf3bac95f472772373c9211e7d4906097
theorem omega_equivalence_94 (p0 p1 p2 p3 : Bool) :
    ((!p3 || p3) || p2) = (((!p3 || p3) || p2) && ((!(!((!p3 || p3) || p2))) || (p2 && p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_94

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=1d01bd5d43147ca35a02df2d7b90db504f8d02ece34f2c71e8a23e335adceb35
theorem omega_equivalence_95 (p0 p1 p2 p3 : Bool) :
    (!(p1 || p0) || (!p1)) = ((!(p1 || p0) || (!p1)) && ((!(!(!(p1 || p0) || (!p1)))) || ((p2 || p0) && (!p2 || p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_95
