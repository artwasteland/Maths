// Independent brute-force: enumerate EVERY domino tiling of R x C, count the
// fault-free ones directly by detecting fault lines. No formula, no I-E.
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <vector>
using namespace std;
int R,C,N;
vector<int> board;          // -1 empty else domino id
vector<int> vcross, hcross; // crossings of each vertical/horizontal gap
long long ffcount=0, total=0;
inline int idx(int r,int c){return r*C+c;}
void rec(){
  int cell=-1;
  for(int i=0;i<N;i++) if(board[i]<0){cell=i;break;}
  if(cell<0){
    total++;
    for(int c=1;c<C;c++) if(vcross[c]==0) return;
    for(int r=1;r<R;r++) if(hcross[r]==0) return;
    ffcount++; return;
  }
  int r=cell/C, c=cell%C;
  // horizontal domino (cell, right)
  if(c+1<C && board[idx(r,c+1)]<0){
    board[cell]=1; board[idx(r,c+1)]=1; vcross[c+1]++;
    rec();
    vcross[c+1]--; board[cell]=-1; board[idx(r,c+1)]=-1;
  }
  // vertical domino (cell, down)
  if(r+1<R && board[idx(r+1,c)]<0){
    board[cell]=1; board[idx(r+1,c)]=1; hcross[r+1]++;
    rec();
    hcross[r+1]--; board[cell]=-1; board[idx(r+1,c)]=-1;
  }
}
int main(int argc,char**argv){
  R=atoi(argv[1]); C=atoi(argv[2]); N=R*C;
  board.assign(N,-1); vcross.assign(C,0); hcross.assign(R,0);
  rec();
  printf("R=%d C=%d  total_tilings=%lld  fault_free=%lld\n",R,C,total,ffcount);
  return 0;
}
