#include "udfilter.h"
#include <stdio.h>
#include <string.h>
static udf_database db;
int init(const char*f,const char*t){char e[256];return udf_database_load_set(&db,f,t,398,e,sizeof e);}
int closure(const char*code,int*out){udf_graph g;udf_witness w;if(!udf_graph6_decode(code,&g))return -1;int steps=0,k=1;for(;;){int r=udf_find(&db,&g,&w);out[0]=steps;out[k]=r;if(r==0)return k+1;if(r==1){out[k+1]=w.index;out[k+2]=w.pattern_vertices;for(int i=0;i<w.pattern_vertices;i++)out[k+3+i]=w.map[i];return k+3+w.pattern_vertices;}if(r!=2)return -2;out[k+1]=w.index;out[k+2]=w.pattern_vertices;for(int i=0;i<w.pattern_vertices;i++)out[k+3+i]=w.map[i];out[k+3+w.pattern_vertices]=w.map[w.pair_a];out[k+4+w.pattern_vertices]=w.map[w.pair_b];k+=5+w.pattern_vertices;g.adj[w.map[w.pair_a]]|=1u<<w.map[w.pair_b];g.adj[w.map[w.pair_b]]|=1u<<w.map[w.pair_a];steps++;if(steps>276)return -3;}}
