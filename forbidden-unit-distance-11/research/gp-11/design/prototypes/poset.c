#include <nauty/naututil.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <sys/resource.h>
#define N 448708
#define HS (1<<20)
static char codes[N][12];
static int ht[HS];
static long minmem=999999999;
static uint64_t key(const char*c){uint64_t k=0;for(int j=1;j<11;j++)k=(k<<6)|(c[j]-63);return k;}
static int find(const char*c){uint64_t x=key(c);x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;unsigned h=x&(HS-1);while(ht[h] && strcmp(c,codes[ht[h]-1]))h=(h+1)&(HS-1);return ht[h]?ht[h]-1:-1;}
static void add(int i){uint64_t x=key(codes[i]);x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;unsigned h=x&(HS-1);while(ht[h])h=(h+1)&(HS-1);ht[h]=i+1;}
static void memory(){FILE*f=fopen("/proc/meminfo","r");char b[200];long n=0;while(fgets(b,sizeof b,f))if(sscanf(b,"MemAvailable: %ld kB",&n)==1)break;fclose(f);if(n<minmem)minmem=n;if(n<1572864)exit(99);}
int main(int argc,char**argv){setpriority(PRIO_PROCESS,0,15);struct timespec a,b;clock_gettime(CLOCK_MONOTONIC,&a);FILE*f=fopen(argv[1],"r");char line[256];int n=0;while(fgets(line,sizeof line,f)){line[strcspn(line,"\r\n")]=0;strcpy(codes[n],line);add(n++);}fclose(f);if(n!=N)return 2;FILE*out=fopen(argv[2],"wb");long rel=0,attempt=0,skip=0;graph g[11],h[11],cg[11];int lab[11],ptn[11],orbits[11],degs[11];static DEFAULTOPTIONS_GRAPH(options);options.getcanon=TRUE;statsblk stats;nauty_check(WORDSIZE,1,11,NAUTYVERSIONID);
for(int i=0;i<n;i++){EMPTYGRAPH(g,1,11);int k=0;memset(degs,0,sizeof degs);for(int v=1;v<11;v++)for(int u=0;u<v;u++,k++)if((codes[i][1+k/6]-63)&(1<<(5-k%6))){ADDONEEDGE(g,u,v,1);degs[u]++;degs[v]++;}int seen[55],ns=0;
for(int v=1;v<11;v++)for(int u=0;u<v;u++)if(ISELEMENT(&g[u],v)){attempt++;if(degs[u]==2||degs[v]==2){skip++;continue;}memcpy(h,g,sizeof h);DELELEMENT(&h[u],v);DELELEMENT(&h[v],u);densenauty(h,lab,ptn,orbits,&options,&stats,1,11,cg);char s[12];s[0]='J';memset(s+1,63,10);s[11]=0;k=0;for(int y=1;y<11;y++)for(int x=0;x<y;x++,k++)if(ISELEMENT(&cg[x],y))s[1+k/6]+=1<<(5-k%6);int child=find(s);if(child<0)continue;int dup=0;for(int j=0;j<ns;j++)if(seen[j]==child)dup=1;if(dup)continue;seen[ns++]=child;uint32_t pair[2]={i,child};fwrite(pair,sizeof pair,1,out);rel++;}if((i&1023)==0)memory();}
fclose(out);clock_gettime(CLOCK_MONOTONIC,&b);fprintf(stderr,"{\"vertices\":%d,\"relations\":%ld,\"deletion_attempts\":%ld,\"degree2_skips\":%ld,\"seconds\":%.6f,\"min_MemAvailable_kib\":%ld}\n",n,rel,attempt,skip,b.tv_sec-a.tv_sec+1e-9*(b.tv_nsec-a.tv_nsec),minmem);return 0;}
