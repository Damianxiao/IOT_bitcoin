import random
import heapq
import math


class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None
        self.diff = None

def build_complete_binary_tree_ex(lst):
    heap = []
    for x in lst:
        heapq.heappush(heap, -x)  # 在插入元素时取相反数再插入

    n = len(heap)
    tree = [None] * (n+1)  # 使用数组表示完全二叉树，第一个元素为空

    for i in range(n):
        tree[i+1] = -heapq.heappop(heap)  # 取出堆顶元素时再次取相反数

        j = i + 1
        while j > 1:
            parent = j // 2  # 找到当前节点的父节点
            if tree[j] > tree[parent]:  # 如果当前节点比父节点大，则交换它们的值
                tree[j], tree[parent] = tree[parent], tree[j]
                j = parent
            else:
                break
    tree[0]=tree[random.randint(0, len(lst))]
    return tree

def build_tree(values):
    if not values:
        return None
    root = TreeNode(values[0])
    queue = [root]
    i = 1
    while i < len(values):
        node = queue.pop(0)
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root

def dfs(root):
    if root is None:
        return None
    left_subtree_diff, right_subtree_diff = 0, 0
    if root.left:
        left_subtree_diff = dfs(root.left)
    if root.right:
        right_subtree_diff = dfs(root.right)
    if left_subtree_diff == 0 and right_subtree_diff == 0:
        root.diff = 0
    elif left_subtree_diff == 0:
        root.diff = abs(right_subtree_diff)
    elif right_subtree_diff == 0:
        root.diff = abs(left_subtree_diff)
    else:
        root.diff = abs(left_subtree_diff - right_subtree_diff)
    return root.val

def build_tree(values):
    if not values:
        return None
    root = TreeNode(values[0])
    queue = [root]
    i = 1
    while i < len(values):
        node = queue.pop(0)
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def find_path(root):
    """
    寻找从根节点到叶子节点的一条路径，路径中每个元素是一个元组，
    元组的结构是：（value，diff），其中value是节点值，diff是此节点两颗子树之间的差。
    """
    # 如果当前节点为空，则返回空列表
    if not root:
        return []

    # 如果当前节点为叶子节点，则返回只包含自身信息的列表
    if not root.left and not root.right:
        return [(root.val, root.diff)]

    # 如果当前节点有左右子树，则递归查找左右子树中更小的路径
    left_path = find_path(root.left)
    right_path = find_path(root.right)
    if not left_path:  # 左子树为空时直接返回右子树的路径
        return [(root.val, root.diff)] + right_path
    elif not right_path:  # 右子树为空时直接返回左子树的路径
        return [(root.val, root.diff)] + left_path
    else:  # 左右子树都不为空时，返回较小路径
        return [(root.val, root.diff)] + (left_path if len(left_path) < len(right_path) else right_path)


if __name__ == '__main__':
    lst = [random.randint(0, 10000000) for _ in range(500)]
    tree = build_complete_binary_tree_ex(lst)
    Etree = build_tree(tree)
    dfs(Etree)
    path = find_path(Etree)

    # print_tree(tree)
    print(tree)
    print(path)
