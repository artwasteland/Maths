#include "udfilter.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/resource.h>
#include <unistd.h>
static udf_database db;
static long minmem=999999999;
static void memory(void){FILE*f=fopen("/proc/meminfo","r");char b[200];long n=0;while(fgets(b,sizeof b,f))if(sscanf(b,"MemAvailable: %ld kB",&n)==1)break;fclose(f);if(n<minmem)minmem=n;if(n<1572864){fprintf(stderr,"STOP memory %ld kB\n",n);exit(99);}}
int main(int argc,char**argv){char error[256],line[4096];long counts[3]={0},total=0;struct timespec a,b;clock_gettime(CLOCK_MONOTONIC,&a);setpriority(PRIO_PROCESS,0,15);memory();if(!udf_database_load_set(&db,argv[1],argv[2],398,error,sizeof error)){fprintf(stderr,"%s\n",error);return 2;}while(fgets(line,sizeof line,stdin)){line[strcspn(line,"\r\n")]=0;udf_graph g;udf_witness w;if(!udf_graph6_decode(line,&g))return 3;int r=udf_find(&db,&g,&w);if(r<0||r>2)return 4;counts[r]++;total++;if(r!=1)puts(line);if((total&65535)==0)memory();}clock_gettime(CLOCK_MONOTONIC,&b);fprintf(stderr,"{\"input\":%ld,\"pass\":%ld,\"forbidden\":%ld,\"tu\":%ld,\"wall_seconds\":%.6f,\"min_MemAvailable_kib\":%ld}\n",total,counts[0],counts[1],counts[2],b.tv_sec-a.tv_sec+1e-9*(b.tv_nsec-a.tv_nsec),minmem);return 0;}
