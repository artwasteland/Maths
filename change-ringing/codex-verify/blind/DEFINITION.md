# Two integer sequences, defined verbatim

Below are the verbatim definitions of two integer sequences. They concern
"change-ringing sequences" for 5 bells.

## Sequence C ("cyclic")

Name: Number of cyclic change-ringing sequences of length n for 5 bells.

a(n) is the number of (change-ringing) sequences of length[*] n when we are
looking at sequences of permutations of the set {1,2,3,4,5} that satisfy:
1. The position of each bell (number) from one permutation to the next can
   stay the same or move by at most one place.
2. No permutation can be repeated except for the starting permutation which
   can be repeated at most once at the end of the sequence to accommodate
   criterion 4.
3. The sequence must start with the permutation (1,2,3,4,5).
4. The sequence must end with the same permutation that it started with.

[*]: We define the length of a change-ringing sequence to be the number of
permutations in the sequence.

With this [*] definition of the length of a change-ringing sequence; for 5
bells we get a maximum length of factorial(5)=120, thus we have 120 possible
lengths, namely 1,2,...,120. Hence {a(n)} has 120 terms.

## Sequence P ("path")

Name: Number of path change-ringing sequences of length n for 5 bells.

a(n) is the number of (change-ringing) sequences of length[*] n when we are
looking at sequences of permutations of the set {1,2,3,4,5} that satisfy:
1. The position of each bell (number) from one permutation to the next can
   stay the same or move by at most one place.
2. No permutation can be repeated except for the starting permutation which
   can be repeated at most once at the end of the sequence to accommodate
   criterion 4.
3. The sequence must start with the permutation (1,2,3,4,5).
And does not satisfy:
4. The sequence must end with the same permutation that it started with.

[*]: We define the length of a change-ringing sequence to be the number of
permutations in the sequence.

With this [*] definition of the length of a change-ringing sequence; for 5
bells we get a maximum length of factorial(5)=120, thus we have 120 possible
lengths, namely 1,2,...,120. Hence {a(n)} has 120 terms.
