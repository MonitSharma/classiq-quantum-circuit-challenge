CC = gcc
CFLAGS = -O3 -march=native -Wall -Wno-unused-function

TARGETS = sa4 sa4f lbeam4 lbeam4c kbeam_t3 kbeamS8 kbeam_wirehash kbeam128 lbeam_parity lbeam_partial kbeam_typed_lb

all: $(TARGETS)

sa4: ../sa4.c
	$(CC) $(CFLAGS) -o $@ $< -lm

sa4f: sa4
	cp sa4 sa4f

lbeam4: ../lbeam4.c
	$(CC) $(CFLAGS) -o $@ $< -lm

# loader beam search used for the depth-115 loaders
lbeam4c: ../lbeam4c.c
	$(CC) $(CFLAGS) -o $@ $< -lm

kbeamS8: ../kbeamS.c
	$(CC) $(CFLAGS) -DN=8 -o $@ $< -lm

kbeam_wirehash: ../kbeam_wirehash.c
	$(CC) $(CFLAGS) -DN=8 -o $@ $< -lm

kbeam128: ../kbeam128.c
	$(CC) $(CFLAGS) -DN=8 -o $@ $< -lm

lbeam_parity: ../lbeam_parity.c
	$(CC) $(CFLAGS) -o $@ $< -lm

lbeam_partial: ../lbeam_partial.c
	$(CC) $(CFLAGS) -o $@ $< -lm

kbeam_typed_lb: ../kbeam_typed_lb.c
	$(CC) $(CFLAGS) -DN=8 -o $@ $< -lm

lbeam_asap_caps: ../lbeam_asap_caps.c
	$(CC) $(CFLAGS) -o $@ $< -lm

# kernel beam search with per-wire windows (fused rotation model), used at depth 115
kbeam_t3: ../tail115/kbeam_t3.c
	$(CC) $(CFLAGS) -DN=8 -o $@ $< -lm

kbeam_restore: ../tail115/kbeam_restore.c
	$(CC) $(CFLAGS) -DN=8 -o $@ $< -lm

clean:
	rm -f $(TARGETS) *.o

.PHONY: all clean
