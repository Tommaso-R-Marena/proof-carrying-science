-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=7fe2255facd40420f57be6f7bc6ec0daa1f38c20a81916f1531f6325635b1fb6
theorem omega_equivalence_1 (p0 p1 p2 p3 : Bool) :
    (!((p1 || p3) && (!p0))) = ((!(p1 || p3)) || (!(!p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_1

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=6d2d2a44c1b7fc72d76efa8e80148f71a8fd94645bfd6ee89b8c289b12d129e1
theorem omega_equivalence_7 (p0 p1 p2 p3 : Bool) :
    (!(p2 && p2)) = ((!p2) || (!p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_7

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=c69009f1bcc1ff4a2a7505fe6b087040b786e22c31d5021723c3a69ace949dfa
theorem omega_equivalence_8 (p0 p1 p2 p3 : Bool) :
    (!(p1 && ((!p2) && p1))) = ((!p1) || ((!(!p2)) && p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_8

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=a92710b769f882c55cc4b5c8bac02a1b686d4b7db21cbb1078378e9e6ed31fc2
theorem omega_equivalence_13 (p0 p1 p2 p3 : Bool) :
    (!((!p2) && (!p1))) = ((!(!p2)) || (!(!p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_13

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=ad474dc9dec274ccc71e2d2a53071383c24ded204e8151e6f4051b7e485cd3d8
theorem omega_equivalence_15 (p0 p1 p2 p3 : Bool) :
    (!(p0 && (!p0))) = (!(!p0) || (!p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_15

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e809c38d52af7f8f2bc82bad9df52e06671e244ec966aa019f2c9eb335b30810
theorem omega_equivalence_16 (p0 p1 p2 p3 : Bool) :
    (!((p3 || p3) && ((!p1) || (!p0)))) = ((!(p3 || p3)) || (!((!p1) || (!p0)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_16

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=d494543b6050ebe3a6830d5ae7a19ffbbded4db5becb2afe7d47e858311f9a29
theorem omega_equivalence_19 (p0 p1 p2 p3 : Bool) :
    (!(((p0 || p1) || p3) && (p2 && p2))) = ((!((p0 || p1) || p3)) || (!(p2 && p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_19

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f73692e1d20867ede5093b47f1d4d5522ae776b232733897c1f14aad55898a3f
theorem omega_equivalence_20 (p0 p1 p2 p3 : Bool) :
    (!(p2 && (!(!p3 || p3)))) = ((!p2) || (!(!(!p3 || p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_20

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f323e0af8e82a8f9f01d98001ce3843906f8d4967c34bd1ea675dc5050d0e9db
theorem omega_equivalence_23 (p0 p1 p2 p3 : Bool) :
    (!(p0 && ((!p2 || p1) && (!p1)))) = ((!p0) || (!((!p2 || p1) && (!p1)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_23

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=afa0a3bd61cfb0036c5cb72fd67c2cee59319678c10bd337e1fb88928fafd9b1
theorem omega_equivalence_24 (p0 p1 p2 p3 : Bool) :
    (!(p2 && p1) || (!(!p3))) = (!(p2 && p1) || (!(!p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_24

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=550287dac7b7c807cc8731cb242aaf2de67459ff0c2d4272eac2e2c8171cfaa4
theorem omega_equivalence_25 (p0 p1 p2 p3 : Bool) :
    (!(!(p2 && p3)) || (!(p1 && p1) || (p3 || p2))) = (!(!(p2 && p3)) || (!(p1 && p1) || (p3 || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_25

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=788495b7117f370eaa9ca3c38729e89ba7ecb3193d7dadf5e45fcc4107a9011c
theorem omega_equivalence_26 (p0 p1 p2 p3 : Bool) :
    (!(p3 || p0) || (p1 && p1)) = ((!(p3 || p0)) || (p1 && p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_26

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e2f8ba192b139e43d65636f161cc961d06050889f7fcec81505a87063cbbd035
theorem omega_equivalence_28 (p0 p1 p2 p3 : Bool) :
    (!p3 || (p3 && (p0 || p2))) = (!p3 || (p3 && (p0 || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_28

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=3211ab698d6524ad611a58b64dbf0f8852326ed115a8e087cd208561b5f3c862
theorem omega_equivalence_29 (p0 p1 p2 p3 : Bool) :
    (!p1 || ((!p1) && p0)) = (!p1 || ((!p1) && p0)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_29

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b3011c8424b87cab80590d7177c53a0b25f092db594ce30149f8fd0c1af6ab47
theorem omega_equivalence_30 (p0 p1 p2 p3 : Bool) :
    (!(!p0) || ((p1 || p2) || p2)) = (!(!p0) || ((p1 || p2) || p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_30

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=ca2b6d4771db693931aeba8d5a1bc4d5bb85d7c015bf90bd1860920082099ef9
theorem omega_equivalence_31 (p0 p1 p2 p3 : Bool) :
    (!(p0 || p3) || (!(p2 || p3) || (!p3))) = ((!(p0 || p3)) || (!(p2 || p3) || (!p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_31

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=4a1e9d12fb7bc7b9625e6a6290b93043a6dadbfa11404f8fb75e1df496be1cd5
theorem omega_equivalence_32 (p0 p1 p2 p3 : Bool) :
    (!((!p0) && p2) || p2) = ((!((!p0) && p2)) || p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_32

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=acc1609a9ca12bb88b961a1b2610422b8d9609bf335f584009eeb608b2281443
theorem omega_equivalence_33 (p0 p1 p2 p3 : Bool) :
    (!(p0 && (!p1 || p0)) || p2) = ((!(p0 && (!p1 || p0))) || p2) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_33

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=43f9545fa48dc13b3bae1e12da0687d57425301bdbae98418cdef846d496047b
theorem omega_equivalence_34 (p0 p1 p2 p3 : Bool) :
    (!((!p2) || (p3 || p0)) || (!(p0 && p3) || (p1 && p3))) = ((!((!p2) || (p3 || p0))) || (!(p0 && p3) || (p1 && p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_34

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=a8e4ccaa3bacf1a7b8d62f4da2052c0c3d216b9cffe09241713c079768660a91
theorem omega_equivalence_35 (p0 p1 p2 p3 : Bool) :
    (!(!(p0 && p2) || p3) || p0) = (((p0 && p2) && p3) || p0) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_35

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=da91b13579994d4b8cbdaf1e36d6d1db98388b1012211423ab2204dbf8f932e8
theorem omega_equivalence_36 (p0 p1 p2 p3 : Bool) :
    (!(p1 || (p0 || p2)) || p3) = ((!(p1 || (p0 || p2))) || p3) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_36

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b229bc850bd7998b11cb92fff03b79664fea718c9e734af095efe68ce429d6fc
theorem omega_equivalence_37 (p0 p1 p2 p3 : Bool) :
    (!(!(!p0 || p2)) || (!(!p2))) = (!(!(!p0 || p2)) || (!(!p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_37

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=0bd6696c8b4382e03b5d762979a0582f7bf6ea2c7fd9c4d1a188f89c1973ff11
theorem omega_equivalence_39 (p0 p1 p2 p3 : Bool) :
    (!(!p2 || (!p0)) || p1) = ((!(!p2 || (!p0))) || p1) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_39

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=bd7b61f399439c675ac1b5bafbde52f99a28313ae3ffbe64d608f7c4cdab308f
theorem omega_equivalence_41 (p0 p1 p2 p3 : Bool) :
    (!(!p1) || (p3 || (p3 || p3))) = (!(!p1) || (p3 || (p3 || p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_41

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b27f2bcf0741c346797b1bc9c6cb717a517d3e95a3b42adb52fe5755bbc418be
theorem omega_equivalence_42 (p0 p1 p2 p3 : Bool) :
    (!(!(!p2 || p3) || (!p2 || p3)) || (!(!p2 || p1))) = ((!(!p2 || p3) || (!p2 || p3)) && (!(!p2 || p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_42

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=5060baf2a052349c9bb6aeb15e2b2dfdaa83d123af28d2a9ee35fc9fffce78f0
theorem omega_equivalence_43 (p0 p1 p2 p3 : Bool) :
    (!p2 || (!p1 || (!p1 || p0))) = (!p2 || (!p1 || (!p1 || p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_43

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e9a1ea5423ee8cfdb126d09429da37be6a03c08e84c0ae5752d18de5ce00991a
theorem omega_equivalence_44 (p0 p1 p2 p3 : Bool) :
    (!(!(p0 && p1)) || (!(!p2) || (!p1))) = (!(!(p0 && p1)) || (!(!p2) || (!p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_44

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=5a0da1e5d0df06bba91ef494ce1294c7d24d6b09ad8af0d633dffd739432437b
theorem omega_equivalence_45 (p0 p1 p2 p3 : Bool) :
    (!(!(!p0) || (p1 && p0)) || (!p2 || (!p2))) = (!(!(!p0) || (p1 && p0)) || (!p2 || (!p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_45

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b041430815ccaac690b382fc8862e0a2b61ac6fb0346f089dc143746d3f94de6
theorem omega_equivalence_46 (p0 p1 p2 p3 : Bool) :
    (!((!p0 || p1) || p1) || (p3 || (!p2))) = ((!((!p0 || p1) || p1)) || (p3 || (!p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_46

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=1d2a57d71cf5cdba205dea98c7ae594d74029893a00205631169d0729ba6ece9
theorem omega_equivalence_47 (p0 p1 p2 p3 : Bool) :
    (!((!p0 || p0) && (!p1)) || p3) = ((!((!p0 || p0) && (!p1))) || p3) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_47

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=27bff67d7bbb107b15f958dc3cc1430927c9bbe55131740716f1aeb168a91ae7
theorem omega_equivalence_48 (p0 p1 p2 p3 : Bool) :
    ((p0 && p0) && (p3 || p2)) = (((p0 && p0) && p3) || ((p0 && p0) && p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_48

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=1a87ffa7860653ccb8637db2d25b15b8746076f93b5e13c67581519a1a1d6578
theorem omega_equivalence_49 (p0 p1 p2 p3 : Bool) :
    ((!(p2 && p0) || p2) && (p1 || (!p0))) = (((!(p2 && p0) || p2) && p1) || ((!(p2 && p0) || p2) && (!p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_49

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=61dc2471374c22085a6556f5b73591728b16fdbcdf4d7313c7ecfb2b2a5ed5ab
theorem omega_equivalence_50 (p0 p1 p2 p3 : Bool) :
    ((!p1) && (((p3 || p3) || (!p1 || p3)) || (!(!p2 || p3)))) = (((!p1) && ((p3 || p3) || (!p1 || p3))) && ((!p1) || (!(!p2 || p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_50

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b4119a27c5240f446c5dd4eb9094d048d743ee49496845bda24dd0b7032f1854
theorem omega_equivalence_56 (p0 p1 p2 p3 : Bool) :
    ((!(p1 || p1) || p1) && ((p3 || p2) || ((!p3 || p0) && (p3 && p3)))) = (((!(p1 || p1) || p1) && (p3 || p2)) && ((!(p1 || p1) || p1) || ((!p3 || p0) && (p3 && p3)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_56

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e0e5137be52245c27f8366d378fc824479cf0af34849336d563407d47eea39ac
theorem omega_equivalence_63 (p0 p1 p2 p3 : Bool) :
    (p0 && (((p0 || p3) && (p1 || p2)) || p2)) = ((p0 && ((p0 || p3) && (p1 || p2))) && (p0 || p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_63

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=2cdc314f694963d2e6f13d2a6997eff17477f1af189f2089f0c3569bd2e8f757
theorem omega_equivalence_64 (p0 p1 p2 p3 : Bool) :
    (p3 && ((p1 || (!p0)) || (p3 || p0))) = ((p3 && (p1 || (!p0))) || (p3 && (p3 || p0))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_64

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=bb7d173748a94da658eb7a80f45d124ce412933ac405de1d04f40eff9ca24124
theorem omega_equivalence_65 (p0 p1 p2 p3 : Bool) :
    (p2 && (p3 || (!(p1 || p2) || p3))) = ((p2 && p3) && (p2 || (!(p1 || p2) || p3))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_65

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=9f442e1fb953ac1b27cdaf8c0270e4403a6e6c87ee7c6546d132a1295e419c74
theorem omega_equivalence_67 (p0 p1 p2 p3 : Bool) :
    (p2 && ((!p0) || p3)) = ((p2 && (!p0)) || (p2 && p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_67

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=1fd8222282db5f659d04cff98d573dafc5970c0b2874bfaf30c212e76b726a4c
theorem omega_equivalence_68 (p0 p1 p2 p3 : Bool) :
    ((!(p2 || p2)) && (p0 || (!(!p2 || p1) || p1))) = (((!(p2 || p2)) && p0) || ((!(p2 || p2)) && (!(!p2 || p1) || p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_68

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=8eddc12a91dc3a90f830011e160a89b871693b15a52d9569ab9fa25279f25842
theorem omega_equivalence_69 (p0 p1 p2 p3 : Bool) :
    ((!(!p1 || p1)) && ((p1 && p3) || p1)) = (((!(!p1 || p1)) && (p1 && p3)) && ((!(!p1 || p1)) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_69

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=ca0beff3e0c7d45bf9b8154fb392c33445fa0a105f3ee25337bcd6847ce90c07
theorem omega_equivalence_70 (p0 p1 p2 p3 : Bool) :
    (p1 && (((!p0 || p1) && (!p3 || p2)) || ((!p1 || p0) && p2))) = ((p1 && ((!p0 || p1) && (!p3 || p2))) && (p1 || ((!p1 || p0) && p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_70

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=5b1932ca8c224b82e6d5e098da604bdbe64e686f7553d699af91f650abdc7760
theorem omega_equivalence_71 (p0 p1 p2 p3 : Bool) :
    (((p1 && p3) && p2) && ((p2 || (!p3 || p2)) || p3)) = ((((p1 && p3) && p2) && (p2 || (!p3 || p2))) && (((p1 && p3) && p2) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_71

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=fbc28671b7326ffc617e0231d0ba47784726ac15db560dcc044bfc604e6c7466
theorem omega_equivalence_72 (p0 p1 p2 p3 : Bool) :
    p2 = (p2 && ((!(!p2)) || p1)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_72

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=b9bbd1699eb52097e5c2c0b94c58482bcb22bb600642557fbc32eed2b6de3be8
theorem omega_equivalence_77 (p0 p1 p2 p3 : Bool) :
    (!p1 || (p0 && p1)) = ((!p1 || (p0 && p1)) && ((!(!(!p1 || (p0 && p1)))) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_77

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f343e6dc8957123349284e9d49e6794e76b48d843abc920561392a08ee0f060e
theorem omega_equivalence_80 (p0 p1 p2 p3 : Bool) :
    ((!p2) && p0) = (((!p2) && p0) && (!((!((!p2) && p0)) || p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_80

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=97127b15fa83cb4949bce8fa35aa7780ed9cd76c7a3484e1eaec2859dd1d94d5
theorem omega_equivalence_84 (p0 p1 p2 p3 : Bool) :
    (!(p1 && p0) || (p2 || p3)) = ((!(p1 && p0) || (p2 || p3)) && ((!(!(!(p1 && p0) || (p2 || p3)))) || p3)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_84

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f08348773e755e983f4052b64c4aa400b25d733ae529052512edeb00d99ad323
theorem omega_equivalence_85 (p0 p1 p2 p3 : Bool) :
    (!(p0 || p3) || (p3 || p0)) = ((!(p0 || p3) || (p3 || p0)) || ((!(!(p0 || p3) || (p3 || p0))) || (!p2))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_85

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=8e100cc88b11d1c685d3d071c59d4afc6cb7983cb23862700c15107914e50a33
theorem omega_equivalence_86 (p0 p1 p2 p3 : Bool) :
    (!p2 || (p1 || p0)) = ((!p2 || (p1 || p0)) && ((!(!(!p2 || (p1 || p0)))) || (!p0 || (!p3 || p2)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_86

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=f335aea8cee5c20b3885657667114055d496cd123225da85b13f116f87373586
theorem omega_equivalence_89 (p0 p1 p2 p3 : Bool) :
    ((!p2 || p1) && p0) = (((!p2 || p1) && p0) && (!((!((!p2 || p1) && p0)) || (!p0)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_89

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=5767d5684bf86c1bd59c8e59a805fec8a986f6354bb9064b2e566b4d0cf93adf
theorem omega_equivalence_90 (p0 p1 p2 p3 : Bool) :
    ((!p3) || (p1 || p3)) = (((!p3) || (p1 || p3)) || ((!((!p3) || (p1 || p3))) || p2)) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_90

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e349e11f7ee706420405a073daf0e1ff892e4beddd746f70d9bf12afa85092cc
theorem omega_equivalence_93 (p0 p1 p2 p3 : Bool) :
    (!(!p3 || p3) || p1) = ((!(!p3 || p3) || p1) && (!((!(!(!p3 || p3) || p1)) || (!p1)))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_93

-- Experimental Boolean interpretation; scientific intent remains unproved.
-- task_sha256=e049e9f7b7634bfa5bad57f44b1a06fb2eb5fe7023555fda201651d24adcc3ed
theorem omega_equivalence_95 (p0 p1 p2 p3 : Bool) :
    (!(p2 && p0) || (!p2 || p1)) = ((!(p2 && p0) || (!p2 || p1)) && ((!(!(!(p2 && p0) || (!p2 || p1)))) || (!p1))) := by
  cases p0 <;> cases p1 <;> cases p2 <;> cases p3 <;> decide
#print axioms omega_equivalence_95
