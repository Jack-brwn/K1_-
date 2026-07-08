# ===========================================================================
#  Makefile — K1 RISC-V RVV 库编译
# ===========================================================================
#  用法:
#    make              # 编译 libk1_rvv.so (需 riscv64 工具链)
#    make clean        # 清理编译产物
#    make install      # 安装到 ../lib/
#
#  K1 板上可直接用 gcc (原生编译):
#    make CC=gcc CFLAGS="-march=rv64gv -O3"
# ===========================================================================

CC       ?= riscv64-unknown-linux-gnu-gcc
CFLAGS   ?= -march=rv64gv -O3 -Wall -fPIC
LDFLAGS  ?= -shared -lm

TARGET   = libk1_rvv.so
INSTALL_DIR = ../lib

SRCS = preprocess_rvv.c nms_rvv.c verification_rvv.c sensor_rvv.c
OBJS = $(SRCS:.c=.o)

.PHONY: all clean install

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^
	@echo "  ✓ $(TARGET) 编译成功"

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

install: $(TARGET)
	mkdir -p $(INSTALL_DIR)
	cp $(TARGET) $(INSTALL_DIR)/
	@echo "  ✓ 已安装到 $(INSTALL_DIR)/$(TARGET)"

clean:
	rm -f $(OBJS) $(TARGET)
	@echo "  ✓ 清理完成"
