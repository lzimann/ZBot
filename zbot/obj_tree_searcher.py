import os
from xml.etree import ElementTree

class TreeSearcher:
    parents = {
        '/area' : '/atom',
        '/turf' : '/atom',
        '/obj'  : '/atom/movable',
        '/mob'  : '/atom/movable',
        '/atom' : '/datum'
    }
    root = ElementTree.parse(os.path.abspath('obj_tree.xml'))
    @staticmethod
    def find_definition(name, what, parent = None):
        """
        Returns the file and line of a var/proc, given the name and var/proc's parent(no parent means global)
        """
        base_type = None #None means global
        all_name = []
        current_root = TreeSearcher.root
        if parent is not None:
            parent = parent.split('/')
            base_type = parent[1]
            current_root = current_root.find(base_type)
            all_name.extend(current_root.findall(what))
            while len(parent) > 2:
                found = False
                for subtype in current_root.findall(base_type):
                    type_name = subtype.text.replace('\n\t\t\t', '')
                    if type_name == parent[2]:
                        found = True
                        current_root = subtype
                        all_name.extend(current_root.findall(what))
                        parent.pop(2)
                        break
                if not found:
                    break
        else:
            all_name.extend(current_root.findall(what))
        for item in all_name:
            txt = item.text.replace('\n\t\t\t', '')
            if txt == name:
                return item.attrib['file']

def main():
    print(TreeSearcher.find_definition("Meme", "proc", '/mob/living'))

if __name__ == '__main__':
    main()