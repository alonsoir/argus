/* ddos_agg_test_run.c -- DAY273. Arnes de prueba del agregador DDoS en-kernel.
 * Carga el objeto BPF (verificador del kernel = arbitro) y ejecuta xdp_sniffer_enhanced
 * con BPF_PROG_TEST_RUN sobre un flood sintetico (5000 x 482 B UDP a 192.168.100.1,
 * + 100 x 300 B TCP a 10.1.2.3) SIN consumidor del ring. Imprime ddos_victims vs stats[0].
 *
 *   clang -O2 -g -target bpf -D__TARGET_ARCH_x86 -c sniffer/src/kernel/sniffer.bpf.c -o sniffer.bpf.o
 *   gcc -O1 ddos_agg_test_run.c -o ddos_agg_test_run -lbpf
 *   sudo ./ddos_agg_test_run sniffer.bpf.o
 *
 * Limites: una sola CPU (no prueba la carrera multi-CPU); filter_settings=CAPTURE y
 * iface_configs[0..2] se configuran aqui a mano (en produccion lo hace ebpf_loader.cpp).
 */
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <arpa/inet.h>
struct ddos_key { uint32_t dst_ip; uint32_t proto; };
struct ddos_val { uint64_t pkts, bytes; };
struct icfg { uint32_t ifindex; uint8_t mode, is_wan, res[2]; };
static int build(uint8_t *p, int total, uint8_t proto, uint32_t dst_host_order){
  memset(p,0,total);
  p[12]=0x08; p[13]=0x00;                    /* ethertype IPv4 */
  uint8_t *ip=p+14; ip[0]=0x45; uint16_t tl=htons(total-14); memcpy(ip+2,&tl,2);
  ip[8]=64; ip[9]=proto;
  ip[12]=10;ip[13]=0;ip[14]=0;ip[15]=7;      /* src 10.0.0.7 */
  ip[16]=dst_host_order>>24; ip[17]=dst_host_order>>16; ip[18]=dst_host_order>>8; ip[19]=dst_host_order;
  uint8_t *l4=ip+20; l4[0]=0x30;l4[1]=0x39; l4[2]=0x1F;l4[3]=0x90;   /* sport 12345 dport 8080 */
  return total;
}
int main(int c,char**v){
  struct bpf_object *o=bpf_object__open_file(v[1],NULL);
  struct bpf_program *p; bpf_object__for_each_program(p,o) bpf_program__set_type(p,BPF_PROG_TYPE_XDP);
  if(bpf_object__load(o)){fprintf(stderr,"load fail\n");return 2;}
  int pfd=bpf_program__fd(bpf_object__find_program_by_name(o,"xdp_sniffer_enhanced"));
  int cfg=bpf_map__fd(bpf_object__find_map_by_name(o,"iface_configs"));
  int st =bpf_map__fd(bpf_object__find_map_by_name(o,"stats"));
  struct bpf_map *dm=bpf_object__find_map_by_name(o,"ddos_victims");
  struct icfg ic={1,1,0,{0,0}}; uint32_t ks[3]={0,1,2}; for(int i=0;i<3;i++){ic.ifindex=ks[i]; int ur=bpf_map_update_elem(cfg,&ks[i],&ic,0); printf("cfg[%u] update rc=%d\n",ks[i],ur);}
  int fs=bpf_map__fd(bpf_object__find_map_by_name(o,"filter_settings")); uint32_t z=0; uint8_t fc[8]={1,0,0,0,0,0,0,0}; printf("filter default_action=CAPTURE rc=%d\n",bpf_map_update_elem(fs,&z,fc,0));
  const int N=5000, LEN=482; uint8_t pkt[2048];
  uint32_t V1=(192u<<24)|(168u<<16)|(100u<<8)|1u;   /* 192.168.100.1 */
  uint32_t V2=(10u<<24)|(1u<<16)|(2u<<8)|3u;        /* 10.1.2.3 (otra victima, TCP) */
  build(pkt,LEN,17,V1);
  struct xdp_md_u { uint32_t data,data_end,data_meta,ingress_ifindex,rx_queue_index,egress_ifindex; } ctx={0,0,0,1,0,0};
  LIBBPF_OPTS(bpf_test_run_opts,t,.data_in=pkt,.data_size_in=LEN,.repeat=N);
  int r=bpf_prog_test_run_opts(pfd,&t);
  printf("test_run V1 UDP: rc=%d retval=%u (XDP_PASS=2) duration=%uns\n",r,t.retval,t.duration);
  build(pkt,300,6,V2); t.data_size_in=300; t.repeat=100; r=bpf_prog_test_run_opts(pfd,&t);
  printf("test_run V2 TCP: rc=%d retval=%u\n",r,t.retval);
  uint32_t k0=0; uint64_t sv=0; bpf_map_lookup_elem(st,&k0,&sv);
  struct ddos_key k={V1,17}; struct ddos_val dv={0};
  int e=bpf_map_lookup_elem(bpf_map__fd(dm),&k,&dv);
  printf("\nenviados a V1: %d pkts x %d B = %d B\n",N,LEN,N*LEN);
  printf("ddos_victims[V1=0x%08X,udp]: found=%d pkts=%llu bytes=%llu\n",V1,e==0,(unsigned long long)dv.pkts,(unsigned long long)dv.bytes);
  struct ddos_key k2={V2,6}; struct ddos_val dv2={0}; e=bpf_map_lookup_elem(bpf_map__fd(dm),&k2,&dv2);
  printf("ddos_victims[V2=0x%08X,tcp]: found=%d pkts=%llu bytes=%llu\n",V2,e==0,(unsigned long long)dv2.pkts,(unsigned long long)dv2.bytes);
  printf("stats[0] (eventos SUBMITIDOS al ring, ring sin consumidor): %llu\n",(unsigned long long)sv);
  printf("=> perdida del ring medida en kernel = %llu - %llu = %lld pkts\n",
    (unsigned long long)(dv.pkts+dv2.pkts),(unsigned long long)sv,(long long)(dv.pkts+dv2.pkts-sv));
  return 0;
}