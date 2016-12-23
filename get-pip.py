#!/usr/bin/env python
#
# Hi There!
# You may be wondering what this giant blob of binary data here is, you might
# even be worried that we're up to something nefarious (good for you for being
# paranoid!). This is a base85 encoding of a zip file, this zip file contains
# an entire copy of pip.
#
# Pip is a thing that installs packages, pip itself is a package that someone
# might want to install, especially if they're looking to run this get-pip.py
# script. Pip has a lot of code to deal with the security of installing
# packages, various edge cases on various platforms, and other such sort of
# "tribal knowledge" that has been encoded in its code base. Because of this
# we basically include an entire copy of pip inside this blob. We do this
# because the alternatives are attempt to implement a "minipip" that probably
# doesn't do things correctly and has weird edge cases, or compress pip itself
# down into a single file.
#
# If you're wondering how this is created, it is using an invoke task located
# in tasks/generate.py called "installer". It can be invoked by using
# ``invoke generate.installer``.

import os.path
import pkgutil
import shutil
import sys
import struct
import tempfile

# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    iterbytes = iter
else:
    def iterbytes(buf):
        return (ord(byte) for byte in buf)

try:
    from base64 import b85decode
except ImportError:
    _b85alphabet = (b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    b"abcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{|}~")

    def b85decode(b):
        _b85dec = [None] * 256
        for i, c in enumerate(iterbytes(_b85alphabet)):
            _b85dec[c] = i

        padding = (-len(b)) % 5
        b = b + b'~' * padding
        out = []
        packI = struct.Struct('!I').pack
        for i in range(0, len(b), 5):
            chunk = b[i:i + 5]
            acc = 0
            try:
                for c in iterbytes(chunk):
                    acc = acc * 85 + _b85dec[c]
            except TypeError:
                for j, c in enumerate(iterbytes(chunk)):
                    if _b85dec[c] is None:
                        raise ValueError(
                            'bad base85 character at position %d' % (i + j)
                        )
                raise
            try:
                out.append(packI(acc))
            except struct.error:
                raise ValueError('base85 overflow in hunk starting at byte %d'
                                 % i)

        result = b''.join(out)
        if padding:
            result = result[:-padding]
        return result


def bootstrap(tmpdir=None):
    # Import pip so we can use it to install pip and maybe setuptools too
    import pip
    from pip.commands.install import InstallCommand
    from pip.req import InstallRequirement

    # Wrapper to provide default certificate with the lowest priority
    class CertInstallCommand(InstallCommand):
        def parse_args(self, args):
            # If cert isn't specified in config or environment, we provide our
            # own certificate through defaults.
            # This allows user to specify custom cert anywhere one likes:
            # config, environment variable or argv.
            if not self.parser.get_default_values().cert:
                self.parser.defaults["cert"] = cert_path  # calculated below
            return super(CertInstallCommand, self).parse_args(args)

    pip.commands_dict["install"] = CertInstallCommand

    implicit_pip = True
    implicit_setuptools = True
    implicit_wheel = True

    # Check if the user has requested us not to install setuptools
    if "--no-setuptools" in sys.argv or os.environ.get("PIP_NO_SETUPTOOLS"):
        args = [x for x in sys.argv[1:] if x != "--no-setuptools"]
        implicit_setuptools = False
    else:
        args = sys.argv[1:]

    # Check if the user has requested us not to install wheel
    if "--no-wheel" in args or os.environ.get("PIP_NO_WHEEL"):
        args = [x for x in args if x != "--no-wheel"]
        implicit_wheel = False

    # We only want to implicitly install setuptools and wheel if they don't
    # already exist on the target platform.
    if implicit_setuptools:
        try:
            import setuptools  # noqa
            implicit_setuptools = False
        except ImportError:
            pass
    if implicit_wheel:
        try:
            import wheel  # noqa
            implicit_wheel = False
        except ImportError:
            pass

    # We want to support people passing things like 'pip<8' to get-pip.py which
    # will let them install a specific version. However because of the dreaded
    # DoubleRequirement error if any of the args look like they might be a
    # specific for one of our packages, then we'll turn off the implicit
    # install of them.
    for arg in args:
        try:
            req = InstallRequirement.from_line(arg)
        except:
            continue

        if implicit_pip and req.name == "pip":
            implicit_pip = False
        elif implicit_setuptools and req.name == "setuptools":
            implicit_setuptools = False
        elif implicit_wheel and req.name == "wheel":
            implicit_wheel = False

    # Add any implicit installations to the end of our args
    if implicit_pip:
        args += ["pip"]
    if implicit_setuptools:
        args += ["setuptools"]
    if implicit_wheel:
        args += ["wheel"]

    delete_tmpdir = False
    try:
        # Create a temporary directory to act as a working directory if we were
        # not given one.
        if tmpdir is None:
            tmpdir = tempfile.mkdtemp()
            delete_tmpdir = True

        # We need to extract the SSL certificates from requests so that they
        # can be passed to --cert
        cert_path = os.path.join(tmpdir, "cacert.pem")
        with open(cert_path, "wb") as cert:
            cert.write(pkgutil.get_data("pip._vendor.requests", "cacert.pem"))

        # Execute the included pip and use it to install the latest pip and
        # setuptools from PyPI
        sys.exit(pip.main(["install", "--upgrade"] + args))
    finally:
        # Remove our temporary directory
        if delete_tmpdir and tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    tmpdir = None
    try:
        # Create a temporary working directory
        tmpdir = tempfile.mkdtemp()

        # Unpack the zipfile into the temporary directory
        pip_zip = os.path.join(tmpdir, "pip.zip")
        with open(pip_zip, "wb") as fp:
            fp.write(b85decode(DATA.replace(b"\n", b"")))

        # Add the zipfile to sys.path so that we can import it
        sys.path.insert(0, pip_zip)

        # Run the bootstrap
        bootstrap(tmpdir=tmpdir)
    finally:
        # Clean up our temporary working directory
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


DATA = b"""
P)h>@6aWAK2mm&gW=RK-r8gW8002}h000jF003}la4%n9X>MtBUtcb8d8JxybK5o&{;pqv$n}tHC^l~
I+Mavrq?0()%%qLSNv=2JXgHJzNr)+u1xVRS+y8#M3xEJc+D&`xG$ILLcd^)g_Juxq^hK-W7fVro!OK
0X56!kJCu>>lSemZerj<NRnb_5pY*@BbRnay))z6cOd0$kktl;ixvk~RSK31x`tD8ELs+)M5$r2{2j*
dEXb0wclPS}@E&c2>K`FeKt4O?bX9-iiWDY7!D<mQ~UvM9vzD|VKg{exwB&U54-sxm8>YHK31t|U{{>
PE#tZP_+VteGhH)eTGzMZy!aHJ(Q?6Cjc(3MQ0lIm@hktf`o4axNvVCTc)Ts4@VJ>@!hh%K`|2$iKE+
HHx+6sw#7#MJW!3g|Y$%N)ur)tC3;}#CBEQ7CdI~xY=+?Ot(T=34r+9E$`%6N}j>;=NFf=Z&^bu!zEv
3t>Ua&1Gxq!8;Ps7soN%ES($^#>_e*>Ru`El;Z0c`kR05XmE3{WT9s{ZCofrE;qGp;vO#hcs@DjeDR$
tn@v;IglI6VSWzNghfplGqI!0<h0I1-4T3r;??TjQs&6OmeCw>gHwP<*5k}E|s-0tgq2{VgAu^rc%*@
7HRg@?*fSPs9ypVK;PZfg`L*{@Wh4H}=)J&0S$#2!{sXR907wMxwCB>Zm0$&8dG^t{{SFIu9BwcKPai
iS)37*53oHqWOqTV)O3RPrz%ERGmE0Tun4O(ssPA=8(oYCvxpzPymKk}-Q$?RIdE=IK(@bmxe)jVQYH
8{VWs)8KiU3x%fE5{sAyYgujXSqq0M!Jcq(%y4NcRLa4k(bC--&}_#|G%=iwT(weU1)OKQ+;gdjz%u)
oWwP6Kw|to?PIw?Km1kAC7Ms_kh)WuY*}FOiLCVc@zRudBQ9tsceu3uNfZ`pomDWvf`>KU^QgE|jC3f
JeGPP6hUu>U2ZL8-0vz>6l;DW>Cpc;OqR~k!*C(#5^E>jBZX2(m7SL-6X;oqX)fNgKHx<25fw`lciam
T?0Sq;<*0efo>>~_mb!wtQ8FET)G{S3%GLx;TuGy_0I*8^0_3ZXQ@aNJf0K2y8VP7S+U1FD)Lc1YZU5
_=?sZ~~HXI3ze#a`M|s-Y_t#noGnybn*-wS~M*gQeu&v6y8yuxLY<q9;0n@W-JMJ0uYy508zYY>!d!A
F!&;`Rs^bRcsWT^vka6lXVZTrPm;4Ks2igbSlrx(sRT^p6}=17w9Ix8?jmITqsTRyjGrANWtnsTD|j$
Y4h<paYnHW51=d#=yy0PVPR28xPL1c&PPKBFnT5A#G$`o~VciTH#|qsF6%jQG1Q0R6Lp!tY%}ORT@1j
I!XUhX%b1PT4WrSG(Rb=IHS6cvPrdCqa6o@jljoC-FWoXJmZGoWK1^u3|=M-D)E-|LIC@LU2z9(*Q$V
eykHz^><5(QWgT)w<ae|Y!yb^7e}PnWMQ-d+S`hPZ!~Kq4b#Rch_wCBaf;NslWq(;Q9B&ASeeNczj`t
LJZmMWX6LG+}gocD`^cV1X!`aIokZt_l`fwT(PDo^ZwzJ$i0fUTZotcBaW{r~vEA`5oc-*wP@-hv6UA
oLz&9(4oUGLM@^kd0Y?l!bmf6-gUh&C*a5p<#uD_4Y=%<nB5`=qdqtSdi3O4TtE5KjSXr43^t{=Xbcw
A1=$Uxm}tzYei=psx$Um3K^#$bEMXCVC14(SpyKB&0BfxSpAu#gWz{1%PL$2(X1OCzyE=eX+=0!UMfb
7=$Tev)VWSDl6k8Q(w=K<E=AX<1f^-W4a%r@FV>b!BhII2*G}|zk1yNsG$GkHLdlf5Gzaat{Tc>$@p`
a+TwY7Wli;y;&R%LORzm+XNlE7>Vmn1j*;EP+Vbf#*@tWz5o0+$?;>TN2)pj76eCD51u1o>jxO7Rd+T
^~TVJZ5V=f+fUt3~2+X?Q3%F77oSob@jkBylRQqf|H}cxNlq|euM|+Co9)Srn2x(&;r3@IQS4AF!H7F
o8r-xn-D4>d|PI6qlSXmJ;9W|=O@}p6HPuvOHX05<L9&{7U)Fm(Yz}NlQ-`!FRw1%yh(q&cy+m$cy6Q
vDwZ*zCcYO{tH6WExz?hq_>>OET{SlFW?YMVB^bOj7$3}o2vCc*b=Na9ht-RL`cQj!G22J9&fIo^m$3
29+HJ>nF|s8yA0n&;d{IKJHp=j(V~BT0>~4G)GPEMc(VQAuvRl`;M6?1>952}1Ot5I~#MYk0Kxxi3Ah
q0z)s{+ML0+{{$39}{osGDzV+%G3gnJXTS9DXfMe;)R!F^lZ>b%Fq4=Wdfk4}wCzJh`hBBYO~_dq4)E
TcmM7`3(}e7h%A3)V?v$2PKRYqb~<uxK^(plFO)SZM~0IY%8iDngjXg9p6)jNviKdF<^@SR^&-uAaig
r#r1axPS%8hf0*;^__DtUn=yIQNxY&=6lFT$?;fbaPB1!>CG)@>9<ahfchB$1pW8rDVDqJ--i45?AjR
0B8c7mEYDNiW~v8a<%<jq&YQ8el_!inSeXKvx>bn8D8{C!mRaF*M5$oJ*5h{7A4fUSurLlk|Ge9D<V{
W>j35F+Yz8R+C*ftDqF;u_LZHS<>zfUP3#rrKI%~GDOrn(Geb3oa;V;xkn21A-6!o~;5)IrK3&>Lg$n
YELmLl9n0XsGIFkW7P7W+cQbn<5G`uwYfk^6+2P*{9yc*!NCRzAqXJB#nGfJ}B!NvFOOhTfndqX%NMl
ise-9(t=Sm&iY#gz#t1Fx4SUsz^%mm(E_;O<CP4yAy56Hgr>VNHrzq3|yB|Hrue#yvyr>(@~yJ^SpJ4
OF^(;kKyNZ_T@JUlux=BG5cWr9_}dO9aCTQY^g^RyvVq;_ugniS6F79aaVdkZH1IkocB$7G|e~a`MGK
!XEswYXIAV1vyQFCC0F2wx<nPqsyd^NE;Vs6>gx`n?t@Ug!osc^vn#KqIIKVLe-1_p#*HV3aVasg00W
>1$}nd<H?N4%IUL7q)`%U4Y-aw?AZCG0;o){R!zvi>UjF>@ZB-R2u;rQ+EVZ$_M+hh_d^Rb?NSN{|#E
&S)jskXLv=z{g*0oLz4Y%3MIH@hdj)++w_Ub=yY}Mo-b#g03!^1v$ME6ew7%D``6|eh~C_r=)A@uzIJ
N=ON&A!*ch(O)=3CM}bncF8OaorQ9gI$?Nhg|T|4M#Y5=A{BwMaNvm<)f~Zvmpdn?c=+yAoeAhSb@87
TMqdtzY}KDV&{B5+UyK14KGjFsSQCzTOv4hWZCpoO%X5b5|_B(AtRH1E(COJCKK$k!;-T@)v_JO?!To
)%RJsP6QFy)qYW9u%;pS0F><gE4vd;3XT?+ji-Eo>J1x>2t;K8GzcH^9$#>PBA1lHjmwg*|^KH_x<*S
=isHy<C%6%xa?|>hr3Ego`XEQrC#p5F9cRF;-Fk<wiuw#Zdf+KO9W1qybT^ra^)ID*8&EC=M;C4?9ET
cl5KePa5RV)4We)kQ|w3`){A<Y(o-Db;lt5lir(yd7hu%u>fs^?iV@3$}~Bb~8<sx8*IVBvR??1v8Q|
H7*QoNy@(N=z@Vu3lfAL%5rQ$-&$KqPV#aBFdQyMV#Y@MU0vHD<|gBpo%q6;`mvo$}yWJ1Bh%J+^oeq
z<ydu?9>GHlja<r_)s^7hvJRC3(bpH&(a@Wy#o9Wda5y_PCdQa$P$4VSYr8>VSWu|(Mo1&i*{s&u@{2
vB>ipRBhNi?@MIwmShkyR`VyPj6zz!LsnP`&@S*HQQ=7(&M}FoqXi;>q5?XVgA32$|3zK777d8C`@``
Q>eL*?-`xmZezko^TratE%IrW;s|5rr@c=|$CA9;DDD_s0Y6IRO)eAR$E8qZkc2N%#@nudxO>zHZlhN
2jBVZNHhBtEQG^Dy!P2rftr_IL518vqjU9{%mWwnSm9`zqI)V0jtc<E<7p#fF6BL=<P$u+vZmGa0_mA
4i`V>q>J>%|@n$Up{%CyZ>kbt$0eh+HnBqyweJn0Mr=_SB26a5@YX!F%-Jxjf(olZ*omrcHoC;?4S<n
5Nhz*1(9=MZ|7cjbL^8P+?wx#a+OMVyne7d{`RSxbd(q1XJuTCy+UrfZDA)+KR|ltMUd~0_1xcH`rJo
^3$+qEK7BT}^M3T@cmSM7?rm^99E{^N)g;K%L00qk5Fi@!#3FqB&$Bm(pbf{mFJ{wma@b&{KVmRF*0$
`lql+a3kh|4j@vtMQl|)|<{MT@7I5G&2e`V9bv#Kq0Q$2?;CU+1ifNEVS(Nyx_EEQ@EsIA<Ae1h24LT
$=4F2KnNd-RBXq8Py^Ym3|_Q$3R!&h_k7XExnHul@Gm)W5<L+qp^uT|)Q0Q2-W>e^vyEI1TC~oScxJA
ydY*9ir{^bUp|3fq&=IMa<q0HWpmm!3s>i&S)*AlSmHC7Z!cjNpdQ`)7^W##r$<hOADi6t-l@D4C&-M
TO7}T%C}i<5uhPCFt7}9Ka;C%IH-s4%5}NyEix$m;41J2#|+yG9hISHsC{YS3|JfiTo}M`Ftio?JmuD
nf8f9g9=Ln+!-#m;!EtAx-6QVZKYA2Y#%GQSkIv=GH@<^U0S&wY^F99@b1o#k7HFpX(m}?WQm26OgYn
NSpM(&^4N&66%m4m#0qi=Y=s3Q+dWBALtQ$5&i;kZDO9FsS^Or5><8wz4V*m_)V>32#VR*ohWuXOIH=
sMUKJ;SFsX7PGyqBJzH9agmUcR4<Z$#7Fqi5KOiS7!Xjg!1zCyrF`+o}2k@x}S&pAdZ@m2jjHc7s#(^
i-Yj&1P=efA`Ab+yDJe1`^*th=2sFbQ(1NDHAXE)+Y6Z(z#qME6l3X2XkkeZGxFJVs(^m_Srklo9vpn
baR{_7E&FMLZVwAAiquC=br^Sn|IU2nvEEVm%(43>tm!(8=?0d&g_`7e6Mm)jWmUWC$m06TLbvadj&v
W2y^Z;Zu-6cO2gdsaIxnc_KJlF8^$0_h`_YKC!7uSl|V7|pGHx0EY)4x)chSpS2a^%2D$kE08mQ<1QY
-O00;m!mS#yyNu*^n0RR9<0ssIH0001RX>c!JUu|J&ZeL$6aCu#kPfx=z48`yL6qa^qhepR4X$Ov65%
(yx$r_O+A$C>v?Xk0z4RXq#_nz%vY>qQ1WfxkqQ3~9gVkXcZ82v&<UC&KZ?;~zIykOJp;MKxvKxYGa3
BiRkSV`2dPR95H=y3#^%=HKq#n&fI6MNq$hoHTWD;CXy`fMOwXo>-nOOFrzI{72-zy%~$-fkObx$UHf
Pxf%%rxUd8a|66~GLQ3R8vL7cRBF~PDAlJ+)moR4V01a?*}x!0kg`h%(L#G~Xb*s9h+(`5M8UCb&3ZG
qcoGOQp;VW#N-&4rFgQZvZ8g0VLYnU307k(&=&*eVS1J1Pdg6a5y1w?^{XcI6_WR=6a(m`zGIdXf614
yQS7FS(g!rYKD_V)ETsH=luY{RzM;)7bdFi;y4^T@31QY-O00;m!mS#zU7>o5o4FCX!E&u=$0001RX>
c!MVRL0;Z*6U1Ze%WSdCeMYkJ~o#`~C_-MPNDSC{2p%hXssYvX9niy1Up%+rwf(&=PH{ktLOsyz49S-
*1KwiJ~NLdg$W}Br8!f!{NM#WDo@JndIc8*lt;#kT_#f&ImpVp0SF<-=eP4oXa2xj#i@B5=vKfRSQlj
Nw;MoD#Dhs$m)ty{eE<0#<OC*PV=>WEu?*t`{uDItC9)H?fWAWIpD}6Jz1HSc9wXX0B~C5viTIHdBUG
8z!i%>vNb=)LD9lwMa&eMg%fp-Q_vdW=q?pi%`%?vT9l-C%(H?e4dt}F;Zg#T7KT5?yzI~o-?PLBaz+
-ptXP(*na_kM#Ejg*tp4B;Iq);Y4EmMeyR@j~`#Q~%(^RP8X)C8FF197BNLTnYN#p9I$XDsQg<OKpmD
GiW))1F!L09Sv@LMLpX}&(?D^_Qf{Elbkc_Fr}s$BUB{;Q>87Jbcsty96bJg;U%%|k^y<fspzt6I{yN
O&tnC6b%FlasTXn;AK~zP`K$UM{}BxcupYn%5r}*SB}?KAc_rNG~pL>G|c|#i^F%)%Dqri_5zk`u=Y5
;gp^(t_{x7w4E0$I%_6OcqzCxkr`R@ik6~S&q$6d&C>sH3PRm@xRH@=yYK{71_J}~(Fov0iSj3d0bl5
j3$!U3Z+QIi=;(-25FWVIoZL^0?k5j0j+23^=2oW>aQQ)vg_P!O3$6%uaHO2q8ckR%f8lX8JyuddAi%
#Ua<1NM36A0pY|;c)03+utlX?gyqp}j5Z6%C{0e`BFU%v*|1+^uxoM1+}V_b*;_(0r*uOLpOd0J5#N}
jD|B!w7(0+_2A3}5)uhDbj?!Ysda{9&TloE#IR5UH20!%R?B@O|<^k{5D9UXai#Fr3ab8ZLe6p{=Zz0
QaDkhdw4t61o8hszVXrtL1o5IHzSBpS{mu?XgHL0R=^AQpA*cfL3MzWglCJPe;w8B4HeQKH$sY%a@Im
r!CqS)>tHwo1)GV0?Q*N$dalc)h3nZova}dlnp8jssU;&3pJo;RBC8e9>uIoE9FPww97BVbCe<)mrVk
ZCh;v&4xL5Ky7P6G@D5n6HXJ-R=YnOH{RRTY?KEu$iMH$`H#($>aM+Q&18L}LsIGoo4x10tA+1DcH=X
G$Tdu<_F|t#sGmUW@!^RBqaV1hN=jgICQl(oCKB(RtUoyC`);48%D`OCC=3y`Ibi-X($O!*NzZ7X6T2
UxmNGPC>U{h6PFrD`3q$|<`CmdX)jWvy=y3(`@G=Gs&^C*G8N>R|X>=Xu|O9-+okFh}66ta?Y3tNd=f
&=MMS6_}XeFx5vaS{V0MDLirTGluqiHhcEW;JNDL2wt#MRn|1hZ27TQ9fPmwUsxZ1C!p|e1Q5Zg*-wK
B3-4Bl=$FW3W|<TiC^3aTlj%_jVZ~Ynanp*2n#kmp@o~1zGc~OK(=`t)29LGn#quYREPr|Cj^516PUm
d_xNc)%&@`gr5yZe+dl4+=~rqBOdf{&<nn&XA){=emPQ^QVG%4x?zd&tSQdfIL|6^4P)+EX1Z5Ax@?A
Vas7Rw@Au?AIwXEa?B;T@j)D50ei`-(jK}VNoOsu5|IQZy9lrPAN#Z`flM$I9A6^FWQnPzFV?~`vso<
mvDZ0FpvG#{R=iFP;+YijBB2zk1O@{)VT>3=2jIeBy3(__YWJcGG{pWa<xEH1tco+a}301;Jec1fUxA
HX=dUfeED-hF71c;?Is;bU3&1RCViv-fx3x|pMoi;MHiz%|EPusKl_x>EqtGbI2NKJi8wWB^_URR<3Y
k(YH2p-{dA+jYpulE)CMz&?UkuYgp5g@feKK_+}zuaUZ{B^X(y8IM|vfvKtGPW>HHD`0om(?PS#Zy@?
jPuTVEz|`E}wr{$w8YHP?%ZyY0luC3ds^x+nK2YNYu$oGL9f%;%9A<UGsqJP5p%i2|g>ONxv50<PPak
lV=W3c@xKRw0Ab^0yGA7)I{^Z3ae=)Y;9a&GR`kQA~(QkrAxYo1bx?hA_uqdeOr*dG4&oI4FxnPWCYr
La8H?qUOBb=(1YFI%hMOFx?my#RRBk9C6swmw^1*Y0}TC4jnAI7BA7}$N^o<@<Z=#goowPywE%8PQ`R
ybg=R%}hU{QE@r=8u;GCSi2^&se{XJ->hT?>TaIT~w;=1pnsG2ms?IwmnX%0kp6#2wo?A_d2h$Yz#Ny
8QTNmt*H4QDJ<U?F)R=Jp_Nw~xQ9xq)|E4ezM;1LQ1?3bBO*2qKBj@LJ&!;&`u37e+p_c#AEwiT!hlL
orxL>Qy$#J|$z_V$T*hsPPNrA~ZrF|!Wldfl)Wj?SumPZ%M3}gxDi_JJs5WYkiS8ibV(FOcW_Za2SDQ
Z4Bc|%N4c4B3{<z@)CJU&!p(w3$+w2sz05vQH!`>?DD!NUIm}C3Zet!gi{Y?=28}>3im9d;*k`35k+2
;R1ySivda|oxZ7Mj^&?cpG%G6cWQ@_*Ce#SKK5e#eX|QM)LLHAkDsArvJQr~)5x3l%DFiO;pjVDu}Gb
%%>j-6|P(=<IG|ny-rc<F^l3$%b!d<m+j-!m>Fg!iT=>gR6bDfwtsr^tJBez(8|VKh`DgY(gQp+$$S1
fH5==&@-?t@ZG0YW*kkiF4ux3ob1u|G-5>F5q;7?4C|y=sRMz>G|Pr)C88)T8%nG#s{{V;?E6L<@a@;
9?buIR4CAfn?d9p^F{#8JtJ^hKO&qMGgusvPif0Jzwn3~n+P-n{wXjo|82T!~B`}S6K&+4v&v&T+*5P
eaWQnF74R$`Z*XwGrrEx#GT3peKOS-tYy1Sh`;BMWU$sj3J`br87AG{u>clPt*=JtlZJGot4UTC6Z(%
mlVP#f;r%&`C({O;HbRf`q$4EO=f%m5}t?Uf^mv{DT;R03JHhv*6lhw$b1ZrBu$o%e*(fv!x2w<s1V_
TSlX=$V|TP6=tRAYnq(CAi3)+TU;KlhATKjV7NF2+&DEW>q+Jy5YzVOwQZXP{$~?U54d`oj!W%3HE&P
^ABgo1mtGTvf2MNZ9FUp88L)Cbj&f3IdaqhXeLoPI+f~dE04L|+{rmlILc<fg#h5|rG*dmBtRms1{7j
97P_41!?)ohF~TH%_u61juTVmU0OW088YtDchLbaU!bdP<Vv&SiF_|HC6-DP*RXK`r_#Hcj@>dXk<~b
p0&lacu7YiI*jeB7ESzJyOnPWV>QM3M~+<wpZ%YunykwdL1>au!<*UOR%y(Jf;;bxgmbyz}9{z}H56R
Dl<GpFbrtu_D<*f6mALHWdn-$y<XScIyS1qluhr)1@4YPMr(hGnbo|Dn5EX?I?FXQC?BxSOBu4^l3)E
uxKefy#sle}W20A2JTa6HK_~$gO+aGFsbN`lA5$;Nr`15PMv+h4lE(nZMmVRW5B9>9dT#o@hb?KJ9Js
nxpgPK-f8rw`apPk{oN~e_?b@<1L3;L}yU7GhCE4YSlfv2WeHI_pXzSb5gZZ7cdTAZBRe6gqdy+Fsbm
2s#7CJad_{<KL5ak+^`If=b%A>o<(gFL*l^gMTae*Tt$Nvuqw3uG#1>=5efWP2?nHOR{@BiZaCxvHyM
VF#?l{_Ks%H2Nh_|ok(%Xbe$ecU<mQb89ofx?<!FDN_SDIwGltrAY|2?a%G%qDeTGzT?*9Fd2rFcYx*
V1zkelf?yuCnRb!G?Xwn#>VJtCH8im~DKH)U;-Rv51SEMZvs;{qA{km&mhbQiZrp3c}X(%&RgsKik=5
UnXXOXu2&h8Xrz*Z2NpH+{w{dmi|EL^a@*Lo&he@V~jQ1y)Vet5@dxs|}OTMnZ!xAzZ5XiEizZlu9Zy
XxFpMq2k!+4afU_>JZl{M0~DnUuR~V_ZmL^q0<v$MW7D&aA&jUY&h5xk|#)W&Eq$F{|5hj@+%KZ88wT
6=cDXvV=M7MHJtprsL8g5vSyv`AlXy|H!GlS0m-@92GUQzzcatdi%?xzktE!*{Zj34kS%9`hI>7v`Fx
0iVsk2kZ>AISVhm30$Ds&jM8VH{4SBodsn-__A5s2JF^sPO1k{Q_a;}$-_o$lj0GCGejTjf#l(%M6Dg
>7LH)cwG@snz2^)JpG^w9QKLfpgZ++46J)sB#@xy-ejXGpMRYOvF7nJJ;DTHn8=;}#?*f<wFoFEooVf
rqfN6h$dg{Ah1txxzM``*4+`s$g1+4Bg?riS2guf&9bS@_}N6wg{s;OaL(0c$g+<vCa#jZbTv^BuCxT
O=iXh+ZjC5>+<^0D`z{mdb^RlwdZ-?#AkkffWC`D@l}Z;Yr#9i{xu@Y*t~u0f^@DFJ$KPaSxA-@kLs3
ZDY)Qj@3TdOu`W26Kn&JP6JByWn2Gn^a>oGtduj)ARb%(|q5HXU0M8-3b%Eu>KTm*NC+NPq7qI>dP)h
>@6aWAK2mm&gW=X57{yU}&007}A000pH003}la4%wEb7gR0a&u*JE^v9BT5WIKxDo#DUqP%9NJ`i0C5
L`7>O<4K+!-h?!J+9F#}&8|cbBy!3M94by`ulUGklRqNozZ21kSEB9L@~q<(Z*ZtJUABVnlSBi<Wd$D
kh0yy6;x2)x}ndh7`rN*S%y#L3q;%sR`XEQTLh^_WQ+!d#+B(e*}hx+3<aMBZp_2J?f*Ro!zG5O81)A
D#zb`E2X6t8zJfoOV#l%FAl7&gv=Fx49Ix9EA**jYLPH+#DOVKUW#_hcUIexycQ)zGYn+u1%aQM?Pz%
_?3!ZBYqoX_iVfJVr42lgecPf0eOobE9Jtgytyz0m8y1R#u>uC_A{)0gN)M*(x{6D+COf7J&1Az{S{I
7{&Mq!43Sh{kXp2s=Eq^Q|BR62rycA6bTvNIF_m|r*#cGWYZ!=g?)>J9-MKY~Vzp%RdBxFN1@J;;z<+
mVlt63Gj&aREz-~;bShpRc0e+Ib~IWV~q;4yn3CtFXCpN2Ef(RIxFifzGtc*}KBq>9zsHF-_t4%B=7`
r(M5+(!6wX?b=6tcA|l^h%QrBedqbmR01)^?u-%o1I`sl~+uak{bsecv<FmNkbnC<XU*H$vv3t#~)^d
+*kpamy$K`$<V!-ksW!Z_vYQ~eA4XhhkJ5G-VTeNHgW!pVMYsDD;G9K3+w92t+EdTE5c#*vL*O7FP2x
@uWOQ!zrIpGCGY|M1^b;@7H+sE&4J2oqi+T#cowX?F}y}`&=vgW->hg9qNi!-6;M-2!7QYP&?jQ+vyj
`6(6%BC(-d}6`NhEI8kaSW_?i&NRW-xqsoJ~LvnI7@claq=6PE9;Nt#@3QM9Wos~qS%;pY^(_FFo$J8
9rx*@4!*k(Vk@O<sBO1@S;Z5YMS8<f2WG47};?e$<b9L*#`~2+u){7WJ!gNEMLY(m5^oVYb8#ZSq291
L>3(<TNBw8TpC4S>VH4NU1t~<NYC9(o53^rV2DCL`}@Z8~?`B`Uf_@;1h^<4Y~RVNh~|7$n1Rlia;P2
DoK+6M{uXsEb8`*R&f5#``x!dXwb?%BsVuC`D|oVNvzed({yjY^iL$Y{?;b5-FroM%<XMHp9!sxt%3?
o^q#?Qu83&s6Z~SNWyhMs{~M-{jJ1}Di7cQcTPQW!3lXX`Flq$}@@u}hd80sgl6-5wBJ*qVN`We1d6R
=&VnrcT>MK5+AwEs5N^7zLhS}6Mz;<SjKo)0};7L?VYDN#BU|-i*thE$10R$jJdZGo`BUC$h86O~?GF
6bbrP<b29|`%Sp}b8dK8!y#-LM+1@*Z<tTd5=>VYOmUEc!6Y5wE)>N;HgAq8zg19`(dZ!fEY~8|sLoY
ZDzY2-Uxdj<!aIT?)sTWG~uti=}Va(fE|=X!(aWmv-~%#@0>N=#DM8h4rN;SU&G@p}S1|Zq6@xr64T5
Kd0t=VwYPA^CdtsKkzXpOr4wom=iwZ*e@?~ZA&`$YWsX~cl+x5q>Suqg+wc_-HSj}@C{3b70$keOlR^
D;zjd;w`O&&x|(b2efQH$u=>`nY>pl{j^OrdR{?5ocOTf6_O(_q%w2%KBes1H2opf~0+j8Qk?g&J>^7
%=F(L18$Upax8{uD%n}dFsOe-e<<XT|C2z%@xCNR6h+hz?o7D|xMv-k*43aa)IxWGY5$x01b8x68|_!
@x`tjN8<;~`k)h1>HS7=*(Q(v{8Un*0idAwK1RC@-u|p0x@SUhW^xlJzrK_bG9QleEVXT6^qL!l$5M;
EaejJXGCD(RYqJuO6T3Ho%&<W-TNxV!8i}s|i3pN_HGt$DtL;!)j;t@VSOoRlN5yiXUto(yF`@Vai(|
aA?Y?Vjj)Wi+OCH{;iXu1Nzfo9mfsbr~vmfmWgffGedPf00$bkMqxOYb?^LF*m!UN-ANZ(MVcTFRY0D
1*JCVWSaD=B*K?Y36!?oq6vsnmbKQY*be>tLrgMLqg?>EuIPQ75A7YwAD339HBITZy4=$Vy8{5$L(hL
oV>FZ4ubX_{Okx(E3dvdygcSHPgC2G@0+>lQcGVUMfm5mMU{=g+1XXL-pqqT*z!o<OFTmefgN8^DBK1
wEJfs6s^%0FJMt>}|g)&|ZGutN@K9%(kqOXm4PDzeLR3BWWR3CHzt;261sLi3h8%GodOv}Ynu0_M`8X
4KO9AXo@oLt{CBMq@8<OaVc(Vb-TA6E(6z=fd%YcOA>j!f(qCJsg=a^e`;vl2?#Pkvm#kIx>tO4NgX7
6)*}9oNTGuhtMNX2-_+MF6*CoKxu*lqxYYG{dD_t@#*#-ACuX^!dXQe42y~#TEHKRSRw3XFEO2>&2Um
ij?5xQ+Mdiv?CQuX7KhQ8E}Sc&UDDb7EDN`QoOjiu=5au_kVHZ)u=GW~J%jk6o*2lWXh-!PvJnWO(%|
(1;x}^n_A?}X0r0;Z00r904ji2{#10&f#!iZ(CvlC)0ViX`G_?!tI?09P8a<O*JORkbup)lSnLn+;eC
iq4d|7VX;w3`w`ELJ0shug1-81se-r|oxK!Y6@De%Y5TyyjxuP{7FR~_$G+4}6d=@594Fq=J%eAhHlf
cnOX@vN+1j?l7iI+Gc&Gmp^yxykc%vI2nSP|R|{6XsDTcx?vFbIqPqJ)6eWB#x$%JQqwe`WX<gGxZ^j
n@YV1HrM2Voz_s3>tItYPm77n&6_MYJFOa4k1f+<$vQnPJpV%Kk5U5Wp$ci@4ZzW%7hS!B2F%civg`r
>SETCAurYE09H^|I{RA$tW$}Q(q&odE9NsR$_w@i|V)XYlXkRSk9RQChS4L??%vA-_1kr7v&S*k->B|
cFAn+|@Zmq%1RL4pjO+ZLjH7bWdu!QnWvD3i|8$h060XH`=Ddv5ZMHmya4T!iCCOOwaJQ!ZMw+RcPL@
!IjZ(_koEd<y9@Bad}Z}Ld92(l{Z$}kQ=*fiPIVnb`FkpuFW_^tyk_6!z6$}GdKsOG=30=&t!R{`*F8
>a66EISihm*j1J4r+c!*^4E9Qb2$Eg!A|`%R*7!fde-^vd7_mSF=a&NeEYTkh~2y=T|pl*qDHEd(E3n
WL)6<-C#?dW>cSlht?0A`#7+LZHwJ2I#VCTc&JW)02qy$rp!yicdcpVn+~edgi~N&cr(voIGf>Z&*HK
vqFEK1)jq-0G97>2+TFcUxDzB~g<}*mC4jo?KtK7I?{Xk$udIv0i(XH40cd95-Xp5SYKM^z0PRRyJxn
AZ=|Vli4}fFw3op^9Cd^7V*375oaQcC0^D)DDtBiL8Gzd3n(IhLN_A$J=vER0cPVs9g`c^NEUY(oxi{
ms(*Z9Ng*>*U(x78*&#}IzIA=SL3TZ%i|yF|q&E<2fVzXNIqOYUDHRSCziq2<GZTtigg7{XuO;O)p<K
zNDwc;mH-b3AvscUC1|0!4ekF^esNZr!91`kzbk$&?HFzzVC!j0C%`fVtDKFpt4L3)0w5ZDEaj0jq+H
9%vmB4~G#dU~~CGQy8Dk5^DGP=$S)DBSmX{e!B~f?B06V#WYW$s|@FSz03y4+>P{jL1A;15g|L1doez
zK+5wR@x($gSQC>iV<-_^?wU$kadY-mo@_E6_*5tpw$D50Va=Zu1m*v@XQq;4E;nRHyoWLnV#{qe9hA
JW;GqKy$vo~MLj(~B5kY`yQ84<&*2c5A!QZ)LT}?}tCWX0BPG)cy^E47d<&#>W_Gxl;wUnwXQ+WAG;R
OSJh4?X-cZj^f5dI!JE<2+h{_xRvCTBSkEe<$FoPj4g!7{^S(8C`b4#uD=w5y-zxMI4eYGA(rlEObxh
{~^_ovPu-310jNh0F(<)(;VX?pVvr#k+MtEN3&g<dA}GbBOulnLw?nTLiO{MZ5rJnE#1Rt{9c&-qiQG
2b?&oE0QiP>o@6YWh2;MUWeJl+rx#d&CN>|`D}+tW^yS=19{nwINd07g#2`ib0*&6fJt-e&OO5T@w~J
XO7RVL`m?ShBbD&?BG8gT5)kqspZLrGO*<(7x2uURQ!w_quGV-|SJ-1c0BZjW*|0r5aDe^!l7~HmE{7
$91za{?z5?;zz-PM?;9nD}y^Nuyhd=%=aPWk{^Bl;Vd5j0iH-ijjDtES)gVDIMCj=SDtyxEZ{<h#`-(
UUDm8gZ5cqpcB&H1Y#cM6jOFt=IQ1-netsNHnXZQ5o3w-C_uDqX>fNnJCY@Y^+6;dL$c%gE^B|4>T<1
QY-O00;m!mS#yynKB`M5&!^NKmY&{0001RX>c!NZDen7bZKvHb1ras%{yyv<2aJv{VNCs4cU9PdS(}W
hYL1`%O;ub;AXmmBr`X--iAQSw9SnyX+<e%-(vs!)q|8s*|F2zvxf~Z(-t4aVpXwTEJjf@GHY3@g(#~
=mxU3sScp|!wv`!;?$=6GwJtJU<w~qot%NqBDaAr9b)mXBWs#|=n757iT~Ri_6S^>sEE+8vC7QL`j8=
I$mwCQT#0QvGD{0C?%#|)y&@Y<~(35V~LT31J7R#zq#Ud7&Ea1Po-U@))sL@<CPf8V{lC@DL5tXj&Z?
RH^s%756Yo2rlI2Vno3tWFn+cWF3%@;-7j4Ejmdj_0{`x1~68O+qCQAGp8^V~xYK9*&kmrsB-5MrT>U
KPn`6ag8Rb-58~x@?=aR%t5qrYh@3$hj%=woxg6k9gd&EwZL8bK`~q{y?srdtpJ^kL&zE2)sq6OvT;L
H#fIecX#Q#s~>Nswr^xdKFPWOq8hslP$tpELVb3S#v=iLKa}-GHWy{l)MY*u%T1GJO`fiSHn~bSumhQ
=>T{O23)OcQWjfb|thZAF;x)HMrB7?6@=3q!rd+6gdpFyg>%K29Gsz^i-9O)5-KH1k7w@jp%j?^zFm;
wzHOScKep1`$+$3vh)~cI#cYpig{oC~2`Q5v#yU}O_VktKAL8Z*Hl;n84V!{zg>&Yo$j~v5)Zxyhs0I
BeaEXw&`RMyY{nk>X@CO}l$4IGq)gk+(!hQ&25<VM9LSg{qASUjk$q4~Tj%`bY!-cW0RiI1{4^U)bIj
49*tk=Oe)VJ?)loe5Iz1~@D}@m`0}6S-Je3XSbQ6NXkZHT=Prs<i?!eza_MJZEvRFpQ<FUJB3w?$9Ki
Z1lKfEO@X<H)u%$nc9wS;64!>+d&hHShiN#LrMxK&(nFU^F_+q#^E)!W9;YI`?65I6kKW}=b+pOxIye
IRnH6%qDrbQ=p9c1fSwf40|y=_p8{Lt#&w<wRF=#&=5DWqO3_veR51R$04bjBO`zVXBc^GqD%T);uw&
Wg4GtNw)+B*6>1DV8>TTS($AzG~;|1>xDZ5e)O4_)X^pmWBK$mQqdK|!*iegG@uq@$Rg!?gKrr1%@R7
A`lzs2#-HGOiMki~Yqk#L3?nJI&vOukK;tl)N{<c2u)nc$Cc*NlHL3kq5+6bX<=Q7)a-ELw$315@WZW
;5FL%+WUvfxU(SOoeU)Hd!*bwj`dSWy&6M^{Dc*-=oZ*^nat1PGU}i_R(79RSFcbR)u%MvdPLjo~;3P
Je%RjcxriWnzPtzaCX>h!k=gH-5M+){!C&(NrPqp;a;Su@((Q<!3OQv$XhZB07Svsk!eb>rcK?dZVH`
%vmaz`l!sK$t?0Hb$S2UG*Bx|$(BVX_in2y7s^U@CWw8M>FCJyBQ46s5)8gTcdUzlvOTB7qvRMgtOr|
5)daeH2YQPU5q0I!4hxUIW5VNw#w<y`bYYp_0qMr;dl+?LB^oeEE%q}wP$1&@=c53lh*kRRoI9B%Lj1
QAD@G@YhkE))R<{*3HnMKTw4R8wE96DLq7R>;Y?|eyns~;6G4)ku>HdWgsc12WYV8wI;{p{1BlQ^g22
Mnz6H2y&}8gxYxj~IW0^A6(wONT#>9pdk`JxfmSe7F@6IrUjLbXI^dsyU3rUl|D+8KB^|yp(`rrXWbR
`5FrPS}SI93ecK0cmq{gEXaK?#ebjQzQ2C|b}FuJZ$I2Ju#4O4`|FGIA4OiSRxmDvMEcB3kR(797;;2
yzzDPw^kcTvxpH4%p1IRgC;j&Z%oH5$v#65II`YU8-9Q7PE`<|p4mNN{Fdq&%;01<47eKPZXZjMP0^E
G_K)x7Fa3{AYXY?Jg(Lw#KPG(h?pSOoaYDQxMEc}*cTPZ}K9;_VuLLJ>zD$~m?kc?LZ?TYpejji~ID)
SVBsi(z%exm*aS{|_x{PZLuUD?!{Jc2`*+ED|2=C?7ndPnTv_{jbwKkH4q5k<S1qbG(AEHAHQwnm?!P
(*ke3kq;&)TU}YwJ)Nv1ub5=A9MmHv>p6e9+nN*jvd8E+Cu3Y10ju#%7Sf&!+6`vyp+R@fBz=XJ)mEZ
FQ&{M6l08N?(PMagCop`aAX_P$Lt`3PRLDl5S)f{9+=re(7d5zpg^&ZL7fVftP&BM$0Bw_add#if(?5
}e2HWZ4}^KpRcdV@T6Y5<D+qxP?(1CeAP(+G2f|MTC45kB3)nI9J7zRJ*v>O}e9P7-;sIk~02nKdvGs
(lW6qoEeW4Sl?ZHvSgb8L>@><EomceubVNVQq#&9hb{ceI)y<Xl&wk~z1yk>4NXCGsO!msgvPx!w%{!
hlAeE7Wck6zm#1=M$Rr)38bKKPebHo2R(E%$63A}-Iv8=DD)^4WSS#(IJdBACSS(?nPJ?|cFtI3^Ira
x!<?Y?P_`*x|<^fkb!>L-u$3LR162+nK7Il30xr7w2N$VycEP$sjN+AhLM@J~VO<T0Mj#!imw{OYyzC
`%y4tfspl5XMj9-2f~1rg@_yNIOz_l3r+;8K>b#=e#GrQs4ck^*zZ9?19Wrsli+BNNI|Ktw5{{QgwU*
xY4i+6^JlfKG=F)d=^zf-^z-eH1KMDUD=~Ug<q9YGB>9sB2LooH9lF^zYY@yEkSV!R;+nE^JKA}Y1f;
mfY@@YQRSC9_eV1BQrP1IxY=Mrju$G0*N!?uCh&SK;Av9-X76?Iq=K0O_M1abcg4`*w0Ckm7PcHQWy~
Y5FHTwp_aG&&6Gc~nLJDMHQO{8*Qg3pK@r4s-&`xHUXiGzw`pO#_nT;U?f9)tX;EMsU<#mO5(!p7b*@
D7?hiV#&iX-dQ$GpfrJTWZxU1(@dGWE)+MtoOM%Y`2_`xfqxpH}`9O%=ns=U`PxxrqDGn%LmGWG-3w6
c(It}x_B^5KulnOl4YlYWCBN|G~%c@EcqbzFn8pk2lllr@5Ck)H<pC!C7c3OA8;Hhr*;dmZZ<h-t0^+
m-aC++!#m$253<hI5LlT+5KKN<1QKQ;sMFW4X(hb<h(Rj)V>jIaMvEfZX-x;(IpE%T1-k~E>CdA?0Zi
c#(e1|(`hytK_?a6Y4X7W5;G!K4M9hKcWgLiZ&M*G!{OwgV;6ix6(H#d~9CL&Yfg>>^Zw9kz1C0I6`0
&0q^E5!%5g%q6Olqx5(;O$g9X-R*JB0T^nU~PLqw%{BclYnlf4Vxt6Bjhq4}7tO3!$d63xgB?s8HI<c
C{9|5sMP!4-?aC`KZLB%)w9$r4~iC*ot@e_cwP*)HCu#+^S6p)8rE9F8(d~4pm(!TSr(6I&ZJ2ei3Jv
$i^>cZHK;-Fi?3aYioZ${n={^BbVx>C$B9aqyqN_^P_#MTi}`V=ui6pJdua^$lHD?7Y7?0a&gf8ja(e
<qW*pI2D2y-u9$S8kYK9FwrppP?7>c(_0!mL1zULz_SY($=&GPAtA=jp2{syJa9;Wq*fim}>n_Slu+2
62+RbrGoUtYDr|ei_585}IVzh@tTO41w1zeiJfFI_<gq22p<l#UzHSum)Vse@7&8VN*+yEL>&0v$mlk
S4E57dv+rw%gkIA@1IKD>Vng|7LsNYD*=PZfXRZzqdO<Qyf5Vv@M=yRN*;2z@g#(2aV%$9)@j6rmI)-
r%E;<QAs;ABgW0AP8OWa{WbkF$X(|7MPqaD;gh7n7o|}XW=?mPKsYH?$D6~iglXN)Y%cI9Y!#@Oxf0%
@_*03pBsL&e-|c~>MW&^VOZKXITH4z6uy6d**T5wu9*V8j#hS`=wvpf6QI~n{$W7mU0vaILi9(xaU$C
M$7@(O+B*?_Sibrc_PW#XWYF<7W(!~sc6!Xp`qy87Jw??9C`<B2YS!L>!oP#n=}H5R5FN(NXk0+ZZuU
!KrF&>P=pr0N*e_=|9^HKn+GG_E<2{ZqOLF0UfS8K%D<~yk4H>O2%AgFIQS=Sk*M-GY?cyDs*oy?a@}
5LoUIB3~&hM`-aq~<02r|vr<FGTng{PC_)J?ilO&Z?ckHNicF_Fw#tFPR6tH4JU;b2?2lejX7LA^o<D
nU|qE8FU)zB+&h(cl#9%v8|qK^+k#6Ok}y-6Gtd>|G0|94xo$RjOUhEs*r(SA81><hFIV53lQ=Z6_XT
`}XH{(sSad``if=_|5Edg<=8C&db7rp1I5(JSW#Ro$biLlry2=n$>%J=%9>l3^rvvnF{)6vXhqPvxb=
@hU`)+a7HfJ40km?p(*C;)M0Q%w^-PZSt;XcPdXM7#S?L!WvT)tt~B)4;uQ9Ix-VO?ur*L<I|t}Z#c6
?MLpTjD$hMr%Qq2_2Ux_uK^$xs^pF83@Aj(Q+<z@p>rK{h>%Fsl-FR4gWHo}w}wFAo`Ld922t+NNVS>
>j}{4o+|Be$ShbdK%Tq_EoBO{DbBk2dW1lopRJY2qK8qk@Nne^b#5&c<&qeC$*F(+b}Jy??y$-8kvOA
%j#mL9@pJkObMAw|*h;K8YJh*bv&T#AQHBg`V7zK$FIyFBn9Y-RwccIH;!$e8i|9ZZG!HW#HQt1Sb}<
k!Y>|h>loS3Bi3wBl?%&`Fsp-CDzJBhm;Lu0S|Dij@1wV8aRr*X#U`+cvx6KwO}gU)BnX8^N7npoG>`
~^Fb5Cxfb#WzvJ1Qk*Cq#&ptTlKKH~1-5SqF2YaG`wm_u2vqzpk9e)A`pX`oXn%OARq!r(19p(s6a`C
d6@uYpc7{Gm5y_LPKKxw&kOW1ohU9dVv$AyX&!$Q+zcn9^EgPXws&;ZdOqV4D(j`eS!WW8!RV&?*cP9
Iz4+SMaF0rRiqNV5T>#;D<Q{h)R#NzeWq^-U(LH7Mq@*R82vQ&{`jhXxw&&(S0iKLfDN8VmvYrONb%q
8sUh@&*kzKo=w1vL&<5i5=;n+E*X}sQ#7%!^<hts8;TJ&b_jrUOH%Djqwpa2c@_Hn?o?)$YmS$dSp4o
>VU=MnyIA|b0-Ft^|WJD(z%ky&LS#l9QKWxj+bgHs~#MGoSuVV@@P%kup0E`C|nm5VqnM$N(C@6><QY
`4cGMAv|%Ftv~`fCVS$0JxEdE@SA&(-Xmh%GxDD%^q%btK9Vw?v4qHMyZwB*RIq8h%1!nPC=wF=~X5L
h)*5yK@&}?mX2dfkK;Z~#S4Zht1e}x<~DGJqBs|Lq+$z{~wdq0A+L)5|S&7yoN@=`9~3~yL;>A?1P(L
}lvap`41Y{DHYvFnk{pXAo0ZSlXlIxHps!`6-`%xFSzJbg$nvK7x<)}<R&uT+Y!i(VEjWB!5Ct&+Qis
Z^c=DI%G#%F~4g6WXBfPb$J*)M6V~Zse}^imEyI@KZ*Oo)yj6(M3q)!6x3T4)o-MxZFO8>K{bx>jf(R
?e8?Aski-5Tw&@EJF}j<0iHJF_!LP0{lumQ(3KazVE0vBm-WtK3R}nVxo^f^p;Z95b1ZU4G-xk730M0
UbGZbNV!m}mojPlVv(L<0{{GFsp2~T)P)U-+;?;ggmTwbBF(zY4Da+u&*t5H^h!D;=y9V*z7?S;09Ei
R$&#yo31P6sT`3rD(9IQLBudVhmDgpIxPxqL)^YPOpVJR9jqfllEwZr-qhgiu!5$|w3FGP2_n5Y5WfT
G#bLkXKYzwIv%oaFG^77Hg$Q9#oa3{SP?e4x96!aFTBo+RGsWC+8ObsO^9<~{=Mk0AGSMQB()?kl-p@
V;})IRm-_W0w`nC^%~=z~RdfcM8Wml|~pjJ8Eqx=AOjWXNh%Dr~71WiNc0Ncke2?BXzitnO|oFGzi~k
>?P03YjiBH+~MjH`4paew?IO!B<^)e0_+_>K%`QVt)5H8C*nQ~VYO57R7qKMnITqJA+*886XFG9n4~U
y7>AFTz)bLC<KPJsxNrQBw|frxH>N8+eLNNMTl>!UL*Q$5uGgvf800|GJ|z-7HtL&qU-I;Q_K85yU^-
soA3e?JKl5_cf4F-8zJ==J{iUfgy>GBJ+dDZQER60OpD8cy2Lu(n9(1pm#7jh}+W+b+Lj7Eo4dR2nQL
BgQb1n@J`84`FI;ut5-;UVwzGoO6)=9pA-CePuPl%w3aKM^{PqV(jEMV8(>w9lUU%mw~*5t#Y4((~-L
W9Zf4xcBQ_ug0hi${sDq-Hv3_v>Q<iX5KCl^uH~_#H@-{{v7<0|XQR000O8HkM{dn{PY_m?HoHt9<|f
4*&oFaA|NaWN&wFY;R#?E^vA6J^gdrHkQBpufQsk5!K3!lkM)zx#RAoX}a-knq=an-94|5rbI|$O_5r
Hw5_JOzy00^00JN-JK6h~*;`L0mPp{?;Q{aa0bbPAS|rJ$ZQ5EUiOAQRs%}I&Q&rJ6GU4wB2m1MZnVX
Mto#sW{HhH1Uqor&%sj^>xR#j;}7u9l^mrL_?ov&rH-ALQEvY$3Z+AOMiZNAsid{QeM&3@b3E{$Ao7I
`5L4w`y<d?4V*G*X2S4@6o0Ev3gVo}MM|UY>~)@vd&=fxMl|O(RaJ@$<T_>f@l<_i3R3?gGiQ$v1IwE
z7K`W0l{=>*`vnxUGvKpP2zSX|1G4mEgw-eZPPATK=t-s&N45Cw2t@ih~YMAg@YgAe@$}NeiGMJfs;-
#fwy}e#q52ZRV@4>$=KhVY|KAzB%pQ(W;tPk=hh_BX66jsMk#`<y7GMq)npoU*JoYLxXe+Q*BmLBHzH
zES+Dqn<UEtpHy8@<3!%(s!>zXmK%7T;1ccx@bvAo7pFfyPoDqz-Sbyxr>|d~O~oAM-L3(JIm|dw?QB
z5bE(uMm`N<ld6mKTv)j9Esw9)}P=-wr3D{b&rA*`bO3pRH)lDhuu!r8-rg>gwvTPD~8a7n2X*W$(6)
Ksvd6AhOXV2fgfAjA3>z8NA*^AR3!fs3026NLEKf@;KA<^ch#dm;YQKi|Nx?0vijBisQdHC>blb7C9i
fW#E`{<^IH3u3M5`L}I`byTcKwX#Xxor#|dwV?C(y+|1>HC~uUdL&cZW>uznBS&KKILbyh2On<qrdC}
(Kaj7{V9A#5Zo6&<#T+rr?<}#&tAWRjrJ~i_Tv4kKP6|U|NeX`-b%Fr5)JUP1>$iI$it+RO+8Q2{X?s
!Zs#b0yWs(KU}agVyveWSclo^8(;wL<U3R@$cKo*AW1iw}uF9saif$-)_KctHq_NwPzu3XPhh0H1`n_
ORUE!uNO<%%y5=wg{qG@}(F6zxZnHM>*)4{<(k|2{OAd}C>NLYlMAV%<d?1_zWt`eZYcq+#5D*;wV=E
bkX#PFTohF#Knz5-GcVCu_K3HEkU<mFY+!I4>JFo1!LyKmjgp{}c@*;qXJ5q`UXxuQssHB42@mKY}dl
Ac9LQl@Lr)Dviy$%SYYFea>h*+dgoUZc^7e!m5AQ<owYu)9z`)p7$H3>xB>W+kbspsumkF-w~i#{OWD
9_6f5WIZ|-A4Z4(d>Fy<jizD*(nx{ifG4z`iT<7>AG>LfHrr;!ZM1ri`H5*AO`OKC0}8nYyhtSBn4VT
J2!x>gZZ1TP$;Sh>4Hh)T^KhJtbB25&PEN%5*&Bj7KDJPHbut8ie!HhfP-Jnxu|XSeoq?efs3ZWn*;?
x6<)Q)sP)HCIg}jypbzJ0SS~xxNr`HY890YfM{M!rL6GWl>OgNuJuu(jUf3ET}^2R!cJsaIl(9jUKpi
=vTcbI+}Y5y%;)d%8Pg&i6x{s_`k{U0p%X<e1Q-S$6(m*D_fInxTbyKdA?-mIb#$h!7+H0co8rP#sl1
8vZuMPF%c6kw2n#)?1yf;RD&wn*2rEETuM;`aRUg>Ucul5ZkS8Aq_d$2=QdO!W{kVVKaDeAY6rJIp?r
*pFm6{av^K1Q!)R!dPIt#su186Q6fn;t<d|EfaolJG#vR0JP}*p1QhC?_Sg_t#9&jG!bc;b(>?I>Y1D
$U4&xJ8LE@`(Bbu2AoGWSb%M6ThHUC+;*WziF=(;0Et+V=O#u9dkCTo+`XKtiwH*8e=(>kLfCbYZ0cN
+#%iaj*qxq)wf!LM|<bhz$7Ej{ei>#8W95-T>UQ6^%<JWJ%nK^rz{P_GW`ZTc_*EpcKT)3#dn0|60z7
f%rsrY>looWLnqbd?t7z_-=xYcYSj6P6btK=`vk@goKAN8JVs23l_2XyW~j$-x%BM*xc{IBB;Y<YtJ#
aX-FsEFPQCBZdLo2phP(P)Z$>UcDP#~@jfE4fuC=%8y3LtAHFq)Le&U@7zOs&$%|)})V&sSm_p`vuIR
1W1)PNfLo}TucQxhU*O)J`A>_8orM0TU<x;IcNf--&A#mqV2;+cO3FP%{X9@JHW~L&!C4J3_y>cK19$
Mzvzv^o8^zPA=?bx1~8rla&Ogw!&+{IT+d{d0laxF(Z$TuqEiaG{fQnk=I?P$zI!zKS0M1?$@$^q3wN
+HJs2P%ss(*C0f?ruZ(JOPhSt*<m?m1aI8nyw{P^*O_)<iS+H?Y+^@}IR7akGbV+aLCQ?Nb!`2tcY_@
<IM2(5!=l`B1a3jqyV+`_Q#dfAW*yk$g-+F&B0S5*m(@&Ad3$n)E#PUnq>fn5f$N(_mBV+~Fv0MUrMl
HH&r09zc#m+t!z1_~w4_>s53y}g4i6{~FWJT+<x+|mNXj}<<E`FbCItSAgJgGhItEg<W=y4}{kbCwPi
K*RZl2B^0(2ZQ*+7BJ9!^k94ADp*g4TD!CITKl`>oT-b#GwNgQU}E?Pz~VSFlu3fnN3P+`X(D)TA9x0
^y~sr5PH8l9h(zBfNK<dQpEeDs8u0H{Rdt07yMoz)ul?20V}Q?*3ZF}Bxdg2a{v!5>MyAnd%G2lm3G{
cy(K-UUcS5ggXvLn|OvM*pT-~JgQcYYV_9vK6S%Bn7VJ*@b3K9>&DRMf{34|}LIBeFNv?KxabL&v;fe
=IyplMyT%N5ZZc(Y9l3(Vah_zX>;rd0{X`NVHdaNy%$8T91T=D^1pu`MeMgabtZ7gh_M+pH>~&;;Ka7
%V*dcpwm8$=m~lI~51aEz}%u0t`_&rod1)ckF)q_C$11>Ac*upf=tcKo1pIf8wDCginXB<!7A(i1qJi
^u}<f7<u@1+_@7+Bs{zz3^+q!qlup;3j*%;W^p%@qbEjzW}(APgrqhWX$DoDFVXYH2Bn;%OM<wAWl-I
Ss;zN~-cEMZY%N<2MbR8e89U4e3#|wBAJ*xOF;_7NW<5I|;AxhbVRuv3QTMKt_zby(_%I-Ug;6XTG{T
YKS%N)bI5SI4Ik4Kx45ghTQF`5CkgTwQwsE@IaC5ckOD)s76J33M$`VZPXfNghRud|De$`jlIs`IoX&
qg7?Gf5BK{Gvlcn;2{L978D6Tl&vVOp|&4CmfyPHR2CtiV|P{!9mXBPYV{n$ARiYtG`LO)-Qh)Ab3%Z
1S}PIj+BfPmnLR`paC_`nf+n5PrA0RP@R-keij3Jx-)H(!&NKPVW{IgpVdZN4T>7L_9e<@?W!s>Ok%Q
+oYlSK~QMuSBjuU2F-3noj81bM$v3c*TIueu=kMq>gcO}6X0Zc1>N_A-qux?FLKfdPTEyFU*J#4h){;
%k~OZ*6!*q*-LSXgfzr|>!R#x5vx(Svi9sfM+|3uZF>yI&{~m#do0p^h1XeQ5FmH1*l(dLG^!EAa8KZ
Fc4#pZCdl>c8f422YSuUFuw6{~G^kcun%TzUoKWK_UdqX_G>Bqo|bJhZVXiEcdOzYVw<UbTxMWv*XUM
P;~!GPi9iXUo2%;j-`QkF;0(uK4cmB@YyV*5`8rB%S*ME?jIh?`Xo)*#rM3LqHGDX(P-ZzS6%4aic7f
x8+cEeKDsPPYUOjg%RhQ<y!?(d2<u#|$8vKV5QQmv{XI%IHD+PqiBmG~S%p*qp=`M%dd^yqJ5%$-tg!
$y`X;#OdaM+Xpr#8jz@Km>Bl80}Dul`P)p)ww;wUZ|fR0y1bS1mO=m+=@h36kv9~sA=*%)+5v?|Dmqk
iMh}32UO_M&S}mxT0vj%J)PkkPoj?+}*n!8x<vds)Ne?-ETv`mWT;Uoyu&@^s0Tq5xEx`%|!XkmXA+=
!|rnYH4V>^k7FNHWO6>DHopYz^%3p0MG#<-7ikflBHgmWGBq0vP2@^Gq3ds#fY6$ss#1X5@cWU+X|7T
EwSXQ5=h&XuB6Hv*)2bMzy15Tq?I0LWhoa`IH0fePMMEwU3kFZgJz#Ni9EDAHv->Psn~(Ej@Y|FWUI-
H{JCg1mJ2t*1|u<23B<aX?(LL4dE2kueH#7Z20+g#G4357G{mDeuQ_UDT>-i;TnxEb(Er@pfH+&tPDI
CFdUftVQb{;ezw($raOGEAPl=qo+oZPsQnL`Y;J&3E&duq=#VRfLXr<U#XDgT(XNVxiiOF<|)#NWobv
30G?rDXiR>tP*<>@<`g?#vZ>CsEM8O&wtT(_AelZlDTS70$;{xjVhv*!UHyYDy87p$?_PAS<oSnOcRj
U#E`6}{+M+~@9Q3GkYN#UTv+Mey`<Adnr*{gv<x_OdjHAaso<lEe5mQIN8ohw=v*&N$C9ht;dOi*sr3
toERtsqa-{hM!Nh&$A6;1kqK~B4zJ^giWLlkyV4Gt&(;8*dc+F%5fo`Q#c)NL2u*?vQMHZp-|yTvtSl
U1df5Vrpk`kuQ<4&Kh)%s<I0){$Q{2`EDM6l-{Pg>*Qy%RbsUMf47-J*5WS>Y*JYU<?TPfa?Qw?6)?f
DMsHPP3Hs#lXbp%UrTUaX&7Cy7Qclh*$T=zBD=9yL#8fA(^`c?&w+)iHTZuHuob+eEDS}#_0q-zJHQ(
%3fRl!#G0x}3sJV~8JmZuJDG_o8ni%?wn%Hstiaj<EEJzUV-nO84Qm?Oc~8afj(*F+g;O|Kl`Ft6&gU
e9)-o+s=L3BYjxIbs{6@T{_+uz2x>)40YDk>bbqg#{sVh~jG13l(t~)BcfXyK5v<QHK(ChHPy4xJ~6F
^EqU;|P)`A`HxRj>+USg&OzQrvea-2!MeFLL7(M+Zw5RXvvlct|JbfY?Q!N*NBT)+z3Zbp?(Vt`8O%!
*BQ?n;Ucs7AZ*V%m$1_k3LnM@jl+v=q97KTd!qps^fq&uJd`YemDvYk}OhGX(vbVlixW-AVChn<S`OV
fFxS3*u)3;gn}gmP;?<1c$w)yvWl^LRyp8E?absnZ8=B6O6NK)at!}?*$1QsXc;4aI_M5K9%o95$7*|
aU0`2m&jPi&Nq<zis!HFtbig5zLCu2$RAN3x0^w-i(I)OX0iZ>G>#aMeP<j`}>q&Czl3<D~^=ef6{wD
!C@dGGxHWYwrSbLseL8@C>;Qp-B+eC9_$DwWm$D-&(=z18t+I9f4w^v?+{4-kG?Pz>EMGw!+a$}5KoO
a;}2NI|iu36Vc0_a7`x?Rgj$C$W<@`e*c@D=M&j~_h}@87-zmsmN_ZX~jpqFg+-QrHaDnMuQsuW`-mD
-;C4Vau{2_QA>(5(X|X7|vPtvPZBXGi5*FNY{`6h(-oI%4NEcCp(*S>ktz^|4+sh#oBP{pg7bZINboi
1tIpyE}4L9fF^T!XciUCKuru<nR467F4lr+?W(&>$~B2{#=oO2_NGP3%fLbzNQwpI`*8H