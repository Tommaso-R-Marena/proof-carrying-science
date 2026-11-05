-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=6d2d2a44c1b7fc72d76efa8e80148f71a8fd94645bfd6ee89b8c289b12d129e1
theorem omega_equivalence_0 (p0 p1 p2 p3 : Bool) :
    (!(p2 && p2)) = ((!p2) || (!p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_0

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=1465146974eabbd1871c12b09b0af1be3e0774bfd6b0bc8f6d98ae48f0eaa7ac
theorem omega_equivalence_1 (p0 p1 p2 p3 : Bool) :
    (!(p3 && ((p2 && p2) && (!p2 || p1)))) = ((!p3) || (!((p2 && p2) && (!p2 || p1)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_1

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=5e286114463c0765ade5486c8bfcecb4a37f6b5f9ec3d7eb182ae331b3c9e71b
theorem omega_equivalence_2 (p0 p1 p2 p3 : Bool) :
    (!(p1 && (!p0))) = ((!p1) || (!(!p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_2

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=27e6fe5f5b9554194e92f871f05aa76a20ecf16e8690a76a1952249d0acbdc8d
theorem omega_equivalence_6 (p0 p1 p2 p3 : Bool) :
    (!(((p2 || p1) && (p0 && p0)) && ((p1 || p2) && p3))) = ((!((p2 || p1) && (p0 && p0))) || (!((p1 || p2) && p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_6

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f8242407d62da6ef3fe0147d1e61c3b509f67fd841b9c2e1b9b45383aa9659ff
theorem omega_equivalence_7 (p0 p1 p2 p3 : Bool) :
    (!(p1 && ((!p0 || p3) || p2))) = ((!p1) || (!((!p0 || p3) || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_7

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b80f3452ce741faf9e8155dfcc84f48e71bd79e6970ecf8a74c5d322f60d5c96
theorem omega_equivalence_8 (p0 p1 p2 p3 : Bool) :
    (!((!(!p0) || (!p3 || p1)) && ((!p2 || p1) && p2))) = ((!(!(!p0) || (!p3 || p1))) || (!((!p2 || p1) && p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_8

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=828b4b34f8fa8bc791c9c72923fc4e23a5c722e43e247b17db9252e70c6f7c60
theorem omega_equivalence_12 (p0 p1 p2 p3 : Bool) :
    (!((p0 && p3) && (!(!p1 || p2)))) = ((!(p0 && p3)) || (!(!(!p1 || p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_12

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=a7e21859c1cbd6ea44a770679602a902b02aeb9b2487850f426b2ee94d8fde99
theorem omega_equivalence_15 (p0 p1 p2 p3 : Bool) :
    (!(p1 && ((!p2) || (!p3)))) = ((!p1) || (!((!p2) || (!p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_15

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=cb6e2f293842d1f4ec04659ed63f751e08f8a2ceff82adb0592e7da2789ad6a0
theorem omega_equivalence_17 (p0 p1 p2 p3 : Bool) :
    (!(((p1 && p0) || (p0 || p1)) && (p0 && (p2 || p2)))) = ((!((p1 && p0) || (p0 || p1))) || (!(p0 && (p2 || p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_17

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b06a98b86fee6567325a5867eefe5b04eda7968e29283434c41511c4aef3cdbe
theorem omega_equivalence_18 (p0 p1 p2 p3 : Bool) :
    (!((p1 && (!p1 || p3)) && (!p2))) = ((!(p1 && (!p1 || p3))) || (!(!p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_18

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=07f97a22afc2a57552aba415eeb7ca152cd1f16476a0f5022b0e370de8097350
theorem omega_equivalence_19 (p0 p1 p2 p3 : Bool) :
    (!((!(p3 && p2) || (!p1 || p3)) && (!p1))) = (!((!(!(p3 && p2) || (!p1 || p3))) || (!p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_19

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=3e5b08fa45c6c58d9b5e5e060e80aada599b4b0d3d235f68b23a23e8534f940a
theorem omega_equivalence_21 (p0 p1 p2 p3 : Bool) :
    (!(((p0 || p2) && (!p2)) && p2)) = ((!((p0 || p2) && (!(!p2)))) || p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_21

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=ab510c5ae7678e363360628ec0fb39e02b6e2ea2b82313648fb3118b7494d52f
theorem omega_equivalence_22 (p0 p1 p2 p3 : Bool) :
    (!(p1 && (p0 && (!p1 || p1)))) = ((!p1) || (!(p0 && (!p1 || p1)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_22

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=c7abf83bdd884a2263a92dd7fecba6319816b6572d70bbe3df1fa94fcdaec53a
theorem omega_equivalence_23 (p0 p1 p2 p3 : Bool) :
    (!(((p0 || p2) || (!p0 || p3)) && p3)) = (!((!((p0 || p2) || (!p0 || p3))) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_23

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f6168e6b719a053eb58c95efb8f75cd25037ada0bd2157057d057b3f42ed3f2a
theorem omega_equivalence_24 (p0 p1 p2 p3 : Bool) :
    (!(!(p0 && p2)) || (!(!p0 || p3) || p1)) = (!(!(p0 && p2)) || (!(!p0 || p3) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_24

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=d2688d2752fb1cd7fcb3a8aa2dc104615ef2bff40d7f6975669f1503484fd44c
theorem omega_equivalence_25 (p0 p1 p2 p3 : Bool) :
    (!(!(p1 && p3)) || p3) = (!(!(p1 && p3)) || p3) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_25

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=3a91237faed3bf052cf74406dae059a1d807665274073e81cc671153102f52c0
theorem omega_equivalence_26 (p0 p1 p2 p3 : Bool) :
    (!(p2 && (p0 && p2)) || (p0 && (!p0 || p3))) = (!(p2 && (p0 && p2)) || (p0 && (!p0 || p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_26

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=9979d5e26c36624bacb7be51960faa2ebcd4a4288fead2482276d640511e6049
theorem omega_equivalence_27 (p0 p1 p2 p3 : Bool) :
    (!p0 || p0) = (!p0 || p0) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_27

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=231521326ca332a0ca6eb7ba5ce0e3cd5354151367032e3c1a845a8d443f5c1b
theorem omega_equivalence_28 (p0 p1 p2 p3 : Bool) :
    (!p0 || (!(p0 || p3))) = (!p0 || (!(p0 || p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_28

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b10ce383edb6cb6ceddde7407b1ae62ade90d1131f3dd5832a9dfbde8b9c4a4e
theorem omega_equivalence_29 (p0 p1 p2 p3 : Bool) :
    (!(!(p3 || p3)) || p1) = (!(!(p3 || p3)) || p1) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_29

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f446d2c19429c57ccaa2dc2f547f5834a7803b120b3597db8642fd98fa509d41
theorem omega_equivalence_30 (p0 p1 p2 p3 : Bool) :
    (!((!p3 || p2) && (!p3 || p0)) || p2) = (!((!p3 || p2) && (!p3 || p0)) || p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_30

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=8915a725d04debe5044f68fb5e9ac1dd9fec201dee84ac5e0c02e1a1cad3221a
theorem omega_equivalence_31 (p0 p1 p2 p3 : Bool) :
    (!((!p3 || p3) || (p1 || p3)) || p2) = (((!p3 || p3) || (p1 || p3)) && p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_31

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=6a2c1a211d359f22a4451742fa112e6751de9a3c6b38d8193019cfdccd4cae82
theorem omega_equivalence_32 (p0 p1 p2 p3 : Bool) :
    (!p3 || (!p2)) = (!p3 || (!p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_32

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=2b553858218a4a6380f23a766f13338197e5ab49736cfc6ad45274689713bffa
theorem omega_equivalence_33 (p0 p1 p2 p3 : Bool) :
    (!(p2 && p3) || p0) = (!(p2 && p3) || p0) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_33

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=9ea1ef1b456ca33ac2c5fa0ef57ec8ec960965e5510819fc2a0afa6780d1e07d
theorem omega_equivalence_34 (p0 p1 p2 p3 : Bool) :
    (!(p1 && (!p0)) || ((p3 || p1) || (p1 || p3))) = (!(p1 && (!p0)) || ((p3 || p1) || (p1 || p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_34

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=6b1627fcd4555deec39454bbd261a09bf945b972229788d0b35174a506ba6e11
theorem omega_equivalence_35 (p0 p1 p2 p3 : Bool) :
    (!(!(p0 || p0)) || ((p0 && p0) || p3)) = (!(!(p0 || p0)) || ((p0 && p0) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_35

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=4ff179e7b9c8584de666c1708dd536418ccbcfa52d907f2328c115b7602da0b5
theorem omega_equivalence_36 (p0 p1 p2 p3 : Bool) :
    (!((p0 || p0) || p2) || p2) = (!((p0 || p0) || p2) || p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_36

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=967971decdc384e2734bd87ddac29475c164d45566759129ea62b3585d2b67a1
theorem omega_equivalence_37 (p0 p1 p2 p3 : Bool) :
    (!(p1 || (!p0)) || (p2 || p0)) = (!(p1 || (!p0)) || (p2 || p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_37

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=efbf12065fcb2aa9c58c71c8a242798c7bdb5e3c665b9511ec0b19f449d04d94
theorem omega_equivalence_38 (p0 p1 p2 p3 : Bool) :
    (!(!(!p0) || (p3 && p1)) || p0) = (!(!(!p0) || (p3 && p1)) || p0) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_38

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=858487802a3232113df351462fc7c10b684394625cea7016bdc3be5a9f16abc5
theorem omega_equivalence_39 (p0 p1 p2 p3 : Bool) :
    (!(!(!p3) || p2) || ((!p1) && (p2 && p2))) = (!(!(!p3) || p2) || ((!p1) && (p2 && p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_39

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=5f49b7101dc620bc167f5b4081901b5a68eb0f8811899c462e73026a9b40aab8
theorem omega_equivalence_40 (p0 p1 p2 p3 : Bool) :
    (!(p2 && (!p1)) || p3) = (!(p2 && (!p1)) || p3) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_40

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=374952ce390a8aec2601be708cddff1132f5a66db0eb6b34557aa61b3d77063b
theorem omega_equivalence_41 (p0 p1 p2 p3 : Bool) :
    (!(p2 || (p1 || p0)) || ((p3 || p1) && (!p0 || p2))) = (!(p2 || (p1 || p0)) || ((p3 || p1) && (!p0 || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_41

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=8f761c0a0b7e1f731246127e8998c3494d3074431c6a5f69b9b23e825fb14230
theorem omega_equivalence_42 (p0 p1 p2 p3 : Bool) :
    (!(!p0) || (!(!p1 || p0))) = (!(!p0) || (!(!p1 || p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_42

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=829933605178b1e2a23d33d88a63e5b74fdc895069aeb82bb628a65ed68ba71d
theorem omega_equivalence_43 (p0 p1 p2 p3 : Bool) :
    (!((p0 || p1) || p1) || (!p3 || (p1 && p1))) = (!((p0 || p1) || p1) || (!p3 || (p1 && p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_43

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=8102ab9bc478e1362cab5a2f092d0064b022de401f38cb3391821e2df49f45ab
theorem omega_equivalence_44 (p0 p1 p2 p3 : Bool) :
    (!((p2 && p2) || p2) || (!p3 || p1)) = (!((p2 && p2) || p2) || (!p3 || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_44

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=2eeb38119213a8eaefa8dbd6143883c63844fa14ca3a30b37aa1dd83c291edd6
theorem omega_equivalence_45 (p0 p1 p2 p3 : Bool) :
    (!(!(!p2 || p2) || (p0 || p3)) || p2) = (!(!(!p2 || p2) || (p0 || p3)) || p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_45

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=56eee6d05d89ff809c2140e721ed167438eb3075747e703c997b69e6321f7855
theorem omega_equivalence_46 (p0 p1 p2 p3 : Bool) :
    (!p3 || (p0 && (!p3))) = (!p3 || (p0 && (!p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_46

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b72c63927418d4248c35fe93c5cd6c99a4b4674ed0c97b5d730cc932fbd8e4eb
theorem omega_equivalence_47 (p0 p1 p2 p3 : Bool) :
    (!((p3 && p2) && (p2 && p1)) || ((p1 || p3) || (!p2 || p1))) = (!((p3 && p2) && (p2 && p1)) || ((p1 || p3) || (!p2 || p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_47

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=a1fc40da032d49e519812c2b9f52a24dcb0a7d90ee3580bbe02c66d30b94e33f
theorem omega_equivalence_53 (p0 p1 p2 p3 : Bool) :
    ((p1 || (p1 || p1)) && ((!p1 || (!p2)) || (p1 && (!p2)))) = (((p1 || (p1 || p1)) && (!p1 || (!p2))) && ((p1 || (p1 || p1)) || (p1 && (!p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_53

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=182f60e95360f3298457ce4e078f69fbf9fac5b340209e1d8e3e0870725124c7
theorem omega_equivalence_54 (p0 p1 p2 p3 : Bool) :
    ((!(p2 || p1) || (!p3 || p0)) && (p2 || ((!p1 || p1) || (p2 && p3)))) = (((!(p2 || p1) || (!p3 || p0)) && p2) || ((!(p2 || p1) || (!p3 || p0)) || (!((!p1 || p1) || (p2 && p3))))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_54

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=ca9f33cf0d4e0fcbdd9fa1fe32776658b7f2aed873ae1143ef4754bb94d07325
theorem omega_equivalence_57 (p0 p1 p2 p3 : Bool) :
    ((!p1) && ((!p1) || p0)) = (((!p1) && (!p1)) && ((!p1) || p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_57

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=48bcb815b1ab30da262c7cb250b59e0b3e743a559d27c1a55bbbb2b83e83656e
theorem omega_equivalence_58 (p0 p1 p2 p3 : Bool) :
    ((!p3 || p1) && ((p2 || p2) || p2)) = (((!p3 || p1) && (p2 || p2)) && ((!p3 || p1) || p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_58

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=86b9c8f4ee95aed6d1a6bf45486bbfdf727951253cf0f27cda0dd964d6563a8d
theorem omega_equivalence_59 (p0 p1 p2 p3 : Bool) :
    ((!p2) && (p3 || (!(!p2 || p0)))) = (((!p2) && p3) && ((!p2) || (!(!p2 || p0)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_59

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=10c04f389b894e58d6c91e8d329680010d4c597a68fce9c2c16f340bbe2c44b1
theorem omega_equivalence_61 (p0 p1 p2 p3 : Bool) :
    (((p0 && p1) || (!p3 || p0)) && (p1 || (!(!p0 || p3)))) = ((((p0 && p1) || (!p3 || p0)) && p1) || (((p0 && p1) && (!p3 || p0)) || (!(!p0 || p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_61

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=600844e860d34943a8b19d2ebaae550680ea1a12006661829a28047e12b0bb42
theorem omega_equivalence_62 (p0 p1 p2 p3 : Bool) :
    ((p2 && (!p2)) && (((p0 || p2) || (p3 || p1)) || ((p0 || p0) || p2))) = (((p2 && (!p2)) && ((p0 || p2) || (p3 || p1))) && ((p2 && (!p2)) || ((p0 || p0) || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_62

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=354a3f5398c303516181875b8e9f33c246ad97a309deca14ae1d3eadeaeb9dd2
theorem omega_equivalence_64 (p0 p1 p2 p3 : Bool) :
    ((!p2) && (p0 || (p1 && (p2 && p3)))) = (((!p2) && p0) && ((!p2) || (p1 && (p2 && p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_64

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=3d6a60d5b8971b97f06c67a53b3c5cfe620e51021c49b09355c7fd1c3cf18aa0
theorem omega_equivalence_67 (p0 p1 p2 p3 : Bool) :
    ((p0 && (!p1)) && (p3 || p3)) = (((p0 && (!p1)) && p3) && ((p0 && (!p1)) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_67

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=6f8bcd6835fcfe2a8e2a85ef7653894b4f061fc64b5675a852a220086cf6a1ae
theorem omega_equivalence_69 (p0 p1 p2 p3 : Bool) :
    (((p1 || p1) || p0) && ((!(!p2) || p2) || (p0 || (!p2)))) = ((((p1 || p1) || p0) && (!(!p2) || p2)) || (((p1 || p1) || p0) && (p0 || (!p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_69

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=9a36fd46f8c7fa2444ebfcb5f2622426c845281c054ce9df593aae294295f0d1
theorem omega_equivalence_70 (p0 p1 p2 p3 : Bool) :
    ((!p2 || (p3 && p3)) && (((!p3 || p0) || (!p2 || p3)) || (p0 || p3))) = (((!p2 || (p3 && p3)) && ((!p3 || p0) || (!p2 || p3))) && ((!p2 || (p3 && p3)) || (p0 || p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_70

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=49d1499d2a7a6c8d1dcbc54deb5391726ec09f27dee9017f772627bd83f52f18
theorem omega_equivalence_71 (p0 p1 p2 p3 : Bool) :
    (p0 && ((p2 && (p2 || p3)) || ((p1 && p2) && p1))) = ((p0 && (p2 && (p2 || p3))) && (p0 || ((p1 && p2) && p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_71

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=fbc28671b7326ffc617e0231d0ba47784726ac15db560dcc044bfc604e6c7466
theorem omega_equivalence_72 (p0 p1 p2 p3 : Bool) :
    p2 = (p2 && ((!(!p2)) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_72

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=1100ab550748e83231f2b22d60d46fa7c50a7f7367714921da641eb529872fb9
theorem omega_equivalence_77 (p0 p1 p2 p3 : Bool) :
    (p3 || (p2 && p2)) = ((p3 || (p2 && p2)) && ((!(!(p3 || (p2 && p2)))) || p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_77

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=4008c637cbfc409e7d229a1c1aacc14805abf337de81f6b699016cec17473e97
theorem omega_equivalence_79 (p0 p1 p2 p3 : Bool) :
    (!(p0 || p0) || p1) = ((!(p0 || p0) || p1) && (!((!(!(p0 || p0) || p1)) || (!(!p0 || p0))))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_79

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=56b25bbb1ef74074552651e92042cc5bdcd84c9e231f1ce105ce88680aec66f5
theorem omega_equivalence_80 (p0 p1 p2 p3 : Bool) :
    ((!p2) && (p1 && p1)) = (((!p2) && (p1 && p1)) && ((!((!p2) && (p1 && p1))) || (!(p2 && (p3 || p0))))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_80

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=084be885e133492227c7e03967b28369994e88c0afc84ca8e974750166e1f2c2
theorem omega_equivalence_88 (p0 p1 p2 p3 : Bool) :
    ((!p1) || (p3 || p2)) = (((!p1) || (p3 || p2)) && ((!(!((!p1) || (p3 || p2)))) || (!p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_88

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=186b81f9a9676e64062e668778d09aa374d926b8c6c69d12b7c640d0910116d6
theorem omega_equivalence_89 (p0 p1 p2 p3 : Bool) :
    ((p0 || p3) || (!p1 || p0)) = (((p0 || p3) || (!p1 || p0)) && ((!(!((p0 || p3) || (!p1 || p0)))) || p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_89

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=7ec7740e8b70dce71d3dafc45fcd90b822e291de4f8a99a452dcdb427c2d3505
theorem omega_equivalence_90 (p0 p1 p2 p3 : Bool) :
    ((!p0 || p0) || p3) = (((!p0 || p0) || p3) || ((!((!p0 || p0) || p3)) || (!p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_90

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=2f72bf9b7107fa84d539fa0ea54bbc5ec2d78d3bec59202d6ad292e0fa690786
theorem omega_equivalence_91 (p0 p1 p2 p3 : Bool) :
    ((p3 && p2) || (!p0 || p2)) = (((p3 && p2) || (!p0 || p2)) && ((!(!((p3 && p2) || (!p0 || p2)))) || p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_91

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=512bee2ca0de1fd3a75eef5f88dee20946315344689b902ad1dc2a004c5e7989
theorem omega_equivalence_92 (p0 p1 p2 p3 : Bool) :
    (!(p2 || p2) || (!p0 || p1)) = ((!(p2 || p2) || (!p0 || p1)) && ((!(!(!(p2 || p2) || (!p0 || p1)))) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_92

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=9e8813810feae36ef53b1f51fa24921be228f4f374875243dffe544a7b08c617
theorem omega_equivalence_94 (p0 p1 p2 p3 : Bool) :
    (!(!p2 || p1) || (!p2 || p3)) = ((!(!p2 || p1) || (!p2 || p3)) && ((!(!(!(!p2 || p1) || (!p2 || p3)))) || (!(!p3 || p1) || p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_94

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=9be5d0e87e274378b982c90615e075bcae536e0f791052afb0521fd1d48912b2
theorem omega_equivalence_95 (p0 p1 p2 p3 : Bool) :
    (!(p3 && p0) || (p3 && p0)) = ((!(p3 && p0) || (p3 && p0)) || ((!(!(p3 && p0) || (p3 && p0))) || p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_95
